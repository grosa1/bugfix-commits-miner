import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')

import gzip
import json
import re
import os
import sys
from datetime import datetime
from dateutil.parser import isoparse
from model import Repository, Commit, ImpactedFile
from database import exists_fix_commit, store_commits
import traceback


import spacy
# os.system("python3 -m spacy download en_core_web_sm")
nlp = spacy.load("en_core_web_sm")

data_path = 'data'
archives_lower_limit = datetime(2015, 1, 1)

sha_regex = '[0-9a-f]{6,40}'

fix_words = ['fix', 'solve']
fix_stopwords = ['was', 'been', 'attempt', 'seem', 'solved', 'fixed', 'try', 'trie', 'by', 'test']
introd_stopwords = ['attempt', 'test']
bug_words = ['bug', 'issue', 'problem', 'error', 'misfeature']


def extract_date(filename):
    return datetime.strptime(filename.split('.')[0], '%Y-%m-%d-%H')

# (“fix” or “solve”) and (“bug” or “issue” or “problem” or “error”)
def is_bugfix_commit(message):
    return ('Merge' not in message) and any(w in message for w in fix_words) and any(w in message for w in bug_words)


def is_commit_hash(text):
    sha_pattern = re.compile(sha_regex)
    return sha_pattern.match(text)


def parse_bug_keyword_deps(bug_word, sent):
    for bug_token in sent:
        if bug_word in bug_token.text:
            deps = ' '.join(t.text for t in bug_token.ancestors) + ' ' + ' '.join(t.text for t in bug_token.children)
            if any([w in deps for w in fix_words]):
                return True


def parse_fix_keyword_deps(fix_word, sent, is_introd=True):
    for fix_token in sent:
        if fix_word in fix_token.text:
            deps = ' '.join(t.text for t in fix_token.children) + ' ' + ' '.join(t.text for t in fix_token.ancestors)
            if is_introd and all(w not in deps for w in introd_stopwords) and any([w in deps for w in bug_words]):
                return True
            elif not is_introd and all(w not in deps for w in fix_stopwords):
                return True
            else:
                return False


def parse_buggy_commit_id(message):
    buggy_hash = list()
    doc = nlp(message.lower())
    for sent in doc.sents:
        for hash_token in sent:
            # for each token in sent, try to find commit hash
            if is_commit_hash(hash_token.text):
                hash_str = is_commit_hash(hash_token.text).group()
                for anc in hash_token.ancestors:
                    anc_txt = anc.text
                    if is_commit_hash(anc_txt) and not anc_txt.isdigit():
                        return False
                if (not sent.text.startswith(hash_str)) and (not hash_str.isdigit()) and ('revert' not in sent.text):
                    hash_ancestors = ' '.join(t.text for t in hash_token.ancestors)
                    is_bug_ancestors = [w in hash_ancestors for w in bug_words]
                    is_fix_ancestors = [w in hash_ancestors for w in fix_words]
                    # match with " introd", preceded by a space to avoid prefixes
                    if ' introd' in hash_ancestors:
                        is_introd = True
                        if any(is_bug_ancestors) and any(is_fix_ancestors):
                            if all(w not in hash_ancestors for w in introd_stopwords):
                                buggy_hash.append((is_introd, hash_str))
                        elif any(is_fix_ancestors): 
                            fix_word = fix_words[is_fix_ancestors.index(True)]
                            if parse_fix_keyword_deps(fix_word, sent):
                                buggy_hash.append((is_introd, hash_str))
                        elif any(is_bug_ancestors):
                            bug_word = bug_words[is_bug_ancestors.index(True)]
                            if parse_bug_keyword_deps(bug_word, sent):
                                buggy_hash.append((is_introd, hash_str))
                    # match without "introd"
                    else:
                        is_introd = False
                        if any(is_bug_ancestors) and any(is_fix_ancestors):
                            fix_word = fix_words[is_fix_ancestors.index(True)]
                            if all(w not in hash_ancestors for w in fix_stopwords) and parse_fix_keyword_deps(fix_word, sent, is_introd=False):
                                buggy_hash.append((is_introd, hash_str))

    return buggy_hash[0] if len(buggy_hash) == 1 else False


def extract_data(fix_commit):
    try:
        parsed_commit_hash = parse_buggy_commit_id(fix_commit.message)
    except Exception as e:
        parsed_commit_hash = False
        logging.error(f'exception: {type(e).__name__} {e.args}')

    if parsed_commit_hash:
        filter_introd = parsed_commit_hash[0]
        introducing_commit_hash = parsed_commit_hash[1]
        
        if exists_fix_commit(fix_commit, introducing_commit_hash):
            logging.info(f'skip duplicate: {fix_commit.api_url}')
            return

        try:
            repo = Repository(fix_commit.repository)
            bug_commit = repo.get_buggy_commit(introducing_commit_hash)
            bug_impacted_files = repo.get_impacted_files(introducing_commit_hash)
            fix_impacted_files = repo.get_impacted_files(fix_commit.hash)

            store_commits(
                bug_commit, 
                bug_impacted_files, 
                fix_commit, 
                filter_introd,
                introducing_commit_hash,
                fix_impacted_files)
                
        except Exception as e:
            logging.error(f'exception: {type(e).__name__} {e.args}')
            print(traceback.format_exc())
        finally:
            repo.cleanup()


def main(file_names):
    file_names = sorted(file_names, key=lambda f: extract_date(f))  

    logging.info(f'files count: {len(file_names)}')
    logging.info(f'from file: {file_names[0]}, to: {file_names[-1]}')

    tot_processed = 0
    tot = len(file_names)
    for i, file_name in enumerate(file_names):
        logging.info(f'{file_name} # {str(i + 1)} of {tot}')
        try:
            with gzip.open(os.path.join(data_path, file_name)) as f:
                for line in f:
                    json_data = json.loads(line)
                    if json_data['type'] == 'PushEvent':
                        if extract_date(file_name) < archives_lower_limit:
                            try:
                                for commit in json_data['payload']['shas']:
                                    repo_full_name = ''
                                    if 'repo' in json_data.keys():
                                        repo_full_name = json_data['repo']['name']
                                    elif 'repository' in json_data.keys():
                                        if 'full_name' in json_data['repository']:
                                            repo_full_name = json_data['repository']['full_name']
                                        elif 'name' in json_data['repository'] and 'owner' in json_data['repository']:
                                            repo_full_name = f"{json_data['repository']['owner']}/{json_data['repository']['name']}"
                                    
                                    if len(repo_full_name) < 3 or len(commit) < 4:
                                        logging.error(f'parsing exception: repo name or commit data not valid')
                                        continue

                                    commit_msg = commit[2]
                                    if is_bugfix_commit(commit_msg):
                                        tot_processed += 1
                                        fix_commit = Commit(
                                            hash=commit[0],
                                            repository=repo_full_name,
                                            message=commit_msg,
                                            author=commit[3],
                                            api_url=f'https://api.github.com/repos/{repo_full_name}/commits/{commit[0]}',
                                            created_at=isoparse(json_data['created_at'])
                                        )
                                        extract_data(fix_commit)
                            except Exception as e:
                                logging.error(f'parsing exception: {type(e).__name__} {e.args}')
                                print(traceback.format_exc())
                        else:    
                            for commit in json_data['payload']['commits']:
                                commit_msg = commit['message']
                                if is_bugfix_commit(commit_msg) and bool(commit['distinct']):
                                    tot_processed += 1
                                    extract_data(Commit(
                                        hash=commit['sha'],
                                        repository=json_data['repo']['name'],
                                        message=commit_msg,
                                        author=commit['author']['name'],
                                        api_url=commit['url'],
                                        created_at=isoparse(json_data['created_at'])
                                    ))

                logging.info(f'total processed commits: {tot_processed}')
        except Exception as file_error:
            logging.error(f'file exception: {type(file_error).__name__} {file_error.args}')
            print(traceback.format_exc())

    print('+++ DONE +++')


if __name__ == "__main__":
    if len(sys.argv) > 2:
        from_date = extract_date(sys.argv[1])
        to_date = extract_date(sys.argv[2])
        logging.info(f'from date: {from_date}, to date: {to_date}')
        file_names = [f for f in os.listdir(data_path) if f.endswith('.json.gz') and (extract_date(f) >= from_date and extract_date(f) <= to_date)]
    else: 
        file_names = [f for f in os.listdir(data_path) if f.endswith('.json.gz')]

    main(file_names)