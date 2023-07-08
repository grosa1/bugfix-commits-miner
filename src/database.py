import mysql.connector as mysql
import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', <PLACEHOLDER>)
DB_PASS = os.getenv('DB_PASS', <PLACEHOLDER>)


def get_connection():
    return mysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        passwd=DB_PASS,
        database="bugfix_commits"
    )


def exists_fix_commit(fix_commit, introducing_commit_hash):
    exists = False
    conn = get_connection()
    cursor = conn.cursor()

    query = """
       SELECT hash, message, introducing_commit_hash
       FROM fix_commit
       WHERE hash=%s AND message=%s AND introducing_commit_hash=%s;
       """

    try:
        cursor.execute(query, (
            fix_commit.hash,
            fix_commit.message,
            introducing_commit_hash
        ))

        if cursor.fetchone():
            exists = True
    except mysql.Error as e:
        logging.error(f'exists_fix_commit() query exception: {type(e).__name__} {e.args} {fix_commit.api_url}')
    finally:
        if (conn.is_connected()):
            cursor.close()
            conn.close()

    return exists


def store_commits(bug_commit, bug_files, fix_commit, filter_introd, introducing_commit_hash, fix_files):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if not exists_fix_commit(fix_commit, introducing_commit_hash):
            bug_commit_id = insert_bug_commits(cursor, bug_commit, bug_files)
            insert_fix_commits(cursor, fix_commit, fix_files, filter_introd, introducing_commit_hash, bug_commit_id)
            conn.commit()
            logging.info(f'stored: {fix_commit.api_url}')
        else:
            logging.info(f'skip duplicate: {fix_commit.api_url}')
    except mysql.Error as e:
        logging.info(f'store_commits() query exception: {type(e).__name__} {e.args} {fix_commit.api_url}')
        conn.rollback()
        return False
    finally:
        if (conn.is_connected()):
            cursor.close()
            conn.close()
    
    return True


def insert_fix_commits(cursor, fix_commit, fix_files, filter_introd, introducing_commit_hash, bug_commit_id):
    query = """
    INSERT INTO fix_commit (hash, repository, message, author, url, created_at, filter_introd, introducing_commit_hash, introducing_commit_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    cursor.execute(query, (
        fix_commit.hash,
        fix_commit.repository,
        fix_commit.message,
        fix_commit.author,
        fix_commit.api_url,
        fix_commit.created_at,
        filter_introd,
        introducing_commit_hash,
        bug_commit_id            
    ))
    fix_commit_id = cursor.lastrowid
    insert_fix_impacted_files(cursor, fix_files, fix_commit_id)


def insert_bug_commits(cursor, bug_commit, bug_files):
    buggy_commit_id = ''

    query = """
    INSERT INTO bug_commit (hash, repository, message, author, url, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(query, (
        bug_commit.hash,
        bug_commit.repository,
        bug_commit.message,
        bug_commit.author,
        bug_commit.api_url,
        bug_commit.created_at
    ))
    bug_commit_id = cursor.lastrowid
    insert_bug_impacted_files(cursor, bug_files, bug_commit_id)

    return bug_commit_id


def insert_fix_impacted_files(cursor, fix_files, commit_id):
    for imp_file in fix_files:
        query = """
        INSERT INTO fix_impacted_file (name, new_path, old_path, lang, change_type, lines_added, lines_deleted, commit_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            imp_file.name,
            imp_file.new_path,
            imp_file.old_path,
            imp_file.lang,
            imp_file.change_type,
            imp_file.lines_added,
            imp_file.lines_deleted,
            commit_id
        ))


def insert_bug_impacted_files(cursor, bug_files, commit_id):
    for imp_file in bug_files:
        query = """
        INSERT INTO bug_impacted_file (name, new_path, old_path, lang, change_type, lines_added, lines_deleted, commit_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            imp_file.name,
            imp_file.new_path,
            imp_file.old_path,
            imp_file.lang,
            imp_file.change_type,
            imp_file.lines_added,
            imp_file.lines_deleted,
            commit_id
        ))