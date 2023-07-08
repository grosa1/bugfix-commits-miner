import os
from shutil import rmtree
import logging
from pydriller import RepositoryMining
logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')


class Commit(object):
    def __init__(self, hash, repository, message, author, api_url, created_at):
        self.hash = hash
        self.repository = repository
        self.message = message
        self.author = author
        self.api_url = api_url
        self.created_at = created_at


class ImpactedFile(object):
    def __init__(self, name, new_path, old_path, lang, change_type, lines_added, lines_deleted):
        self.name = name
        self.new_path = new_path
        self.old_path = old_path
        self.lang = lang
        self.change_type = change_type
        self.lines_added = lines_added
        self.lines_deleted = lines_deleted


class Repository:
    def __init__(self, repo_full_name):
        self.repo_name = repo_full_name
        if not os.path.isdir('temp'):
            os.makedirs('temp')
        self.repo_dir = os.path.join(os.getcwd(), 'temp', self.repo_name.replace('/', '_'))
        if not os.path.isdir(self.repo_dir):
            os.system(f'git clone https://test:test@github.com/{repo_full_name}.git {self.repo_dir}')

    def cleanup(self):
        if os.path.isdir(self.repo_dir):
            rmtree(self.repo_dir)

    def get_buggy_commit(self, commit_id):
        logging.info(f'get_buggy_commit: {self.repo_name} {commit_id}')
        for commit in RepositoryMining(self.repo_dir, single=commit_id).traverse_commits():
            return Commit(
                commit.hash,
                self.repo_name,
                commit.msg,
                commit.author.name,
                f'https://api.github.com/repos/{self.repo_name}/commits/{commit.hash}',
                commit.author_date
            )

    def get_impacted_files(self, commit_id):
        logging.info(f'get_impacted_files: {self.repo_name} {commit_id}')
        impacted_files = list()
        for commit in RepositoryMining(self.repo_dir, single=commit_id).traverse_commits():
            for mod in commit.modifications:
                file_ext = mod.filename.split('.')
                file_ext = file_ext[-1] if len(file_ext) > 1 else ''

                impacted_files.append(
                    ImpactedFile(mod.filename, mod.new_path, mod.old_path, file_ext, str(mod.change_type).split('.')[1],
                                 ','.join([str(added[0]) for added in mod.diff_parsed['added']]),
                                 ','.join([str(deleted[0]) for deleted in mod.diff_parsed['deleted']]))
                )

        return impacted_files