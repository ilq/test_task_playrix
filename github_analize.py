import argparse
import http.client
import json
import logging
import os
import socket
import sys
from base64 import b64encode
from collections import Counter
from datetime import datetime

# Определяем текущую директорию, чтобы лог лежал рядом со скриптом
curdir = os.path.abspath(os.path.dirname(sys.argv[0]))
logging.basicConfig(
    format=u"%(levelname)-8s [%(asctime)s] %(message)s",
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=f"{curdir}/github_analyze.log")

CONFIG_FILE = 'config.json'
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
TIMEOUT = 10
GITHUB_FORMAT_DATETIME = '%Y-%m-%dT%H:%M:%SZ'
MAX_ACTIVE_USER = 30
DAYS_OLD_PULL = 30
DAYS_OLD_ISSUES = 14


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--url', dest='url', action='store', required=True,
        help='url репозитория.'
    )
    parser.add_argument(
        '-s', '--start_date', dest='start_date', action='store',
        help='Дата начала анализа.'
    )
    parser.add_argument(
        '-e', '--end_date', dest='end_date', action='store',
        help='Дата окончания анализа.'
    )
    parser.add_argument(
        '-f', '--format', dest='date_format', action='store',
        default=GITHUB_FORMAT_DATETIME, help=('Формат даты.')
    )
    parser.add_argument(
        '-b', '--branch', dest='branch', action='store', default='master',
        help='Ветка репозитория.'
    )
    args = parser.parse_args()
    return args


def get_start_date(start_date, date_format):
    if not start_date:
        return

    try:
        start_date = datetime.strptime(start_date, date_format)
    except ValueError:
        raise ValueError(
            f'start_date="{start_date}" cannot be formatted using '
            f'date_format="{date_format}"'
        )

    return start_date


def get_end_date(end_date, date_format):
    if not end_date:
        return

    try:
        end_date = datetime.strptime(end_date, date_format)
    except ValueError:
        raise ValueError(
            f'send_date="{end_date}" cannot be formatted using '
            f'date_format="{date_format}"'
        )

    return end_date


def get_datetime(str_date, date_format=GITHUB_FORMAT_DATETIME):
    return datetime.strptime(str_date, date_format)


def format_str_datetime_github(str_date, date_format=GITHUB_FORMAT_DATETIME):
    # date_time = datetime.strptime(str_date, date_format)
    return datetime.strftime(str_date, date_format)


def get_connection():
    connection = http.client.HTTPSConnection("api.github.com", timeout=TIMEOUT)
    return connection


def get_data_from_url(url):
    root = 'github.com/'

    if root in url:
        url = url.split(root)[1]

    if url[0] == '/':
        url = url[1:]

    owner, repo = url.split('/')[:2]

    return owner, repo


def urlcode_parameters(parameters):
    result = ''
    for key, value in parameters.items():
        result += f'&{key}={value}'
    return result


def generator_response_from_api_github(
        owner, repo, type_api, parameters, auth=None):
    connection = get_connection()
    page = 0
    per_page = 100
    headers = {'User-Agent': USER_AGENT}

    if auth:
        headers['Authorization'] = f'Basic {auth}'

    while True:
        page += 1
        url = (f'/repos/{owner}/{repo}/{type_api}'
               f'?page={page}&per_page={per_page}')
        url += urlcode_parameters(parameters)

        try:
            connection.request('GET', url, headers=headers)
            obj_response = connection.getresponse()
        except socket.timeout:
            logging.error(f"Except 'socket.timeout'. URL: {url}.")
            yield "except 'socket.timeout'"
            raise StopIteration()
        except http.client.CannotSendRequest:
            yield "except 'http.client.CannotSendRequest'"
            raise StopIteration()

        if obj_response.status != 200:
            logging.error(f"Status: {obj_response.status}. URL: {url}.")

        response = json.loads(obj_response.read().decode())

        if not isinstance(response, list):
            raise StopIteration()

        for element in response:
            yield element

        if len(response) < per_page:
            raise StopIteration()


def get_active_users(owner, repo, start_date=None,
                     end_date=None, branch=None, auth=None):
    type_api = 'commits'
    active_users = Counter()
    problems = []
    parameters = dict()

    if branch:
        parameters['sha']: branch

    if start_date:
        parameters['since'] = format_str_datetime_github(start_date)

    if end_date:
        parameters['until'] = format_str_datetime_github(end_date)

    for commit in generator_response_from_api_github(
            owner, repo, type_api, parameters, auth=auth):
        if not isinstance(commit, dict):
            problems.append(commit)
            continue

        if ('author' in commit and commit['author']
                and commit['author'].get('login', None)):
            author = commit['author']['login']
            active_users.update([author])

    return active_users, problems


def print_active_users(active_users, problems):
    for idx, (author, count) \
            in enumerate(active_users.most_common(MAX_ACTIVE_USER)):
        print(f'Active users;{idx+1};{author};{count}')

    if problems:
        print(f"Problems with 'Active users': {';'.join(problems)}.")


def get_pulls(owner, repo, start_date=None,
              end_date=None, branch=None, state='open', auth=None):
    type_api = 'pulls'
    pulls = Counter()
    problems = []
    parameters = {'sort': 'created', 'direction': 'desc', 'state': state}

    if branch:
        parameters['base'] = branch

    for pull in generator_response_from_api_github(
            owner, repo, type_api, parameters, auth=auth):
        if not isinstance(pull, dict):
            problems.append(pull)
            continue

        created = get_datetime(pull['created_at'])
        if ((end_date and created > end_date)
                or (start_date and created < start_date)):
            break

        pulls.update([state])

    return pulls, problems


def get_old_pulls(owner, repo, start_date=None,
                  end_date=None, branch=None, now=None, auth=None):
    old_pulls = Counter()
    problems = []
    type_api = 'pulls'
    parameters = {'sort': 'created', 'direction': 'desc', 'state': 'open'}

    if branch:
        parameters['base'] = branch

    if not now:
        now = datetime.utcnow()

    for pull in generator_response_from_api_github(
            owner, repo, type_api, parameters, auth=auth):
        created = get_datetime(pull['created_at'])
        if not isinstance(pull, dict):
            problems.append(pull)
            continue

        if ((end_date and created > end_date)
                or (start_date and created < start_date)):
            break

        delta_days = (now - created).days

        if delta_days > DAYS_OLD_PULL:
            old_pulls.update(['old'])

    return old_pulls, problems


def get_issues(owner, repo, start_date=None,
              end_date=None, branch=None, state='open', auth=None):
    issues = Counter()
    problems = []
    type_api = 'issues'
    parameters = {'sort': 'created', 'direction': 'desc',
                  'filter': 'all', 'state': state}

    if branch:
        parameters['base'] = branch

    for issue in generator_response_from_api_github(
            owner, repo, type_api, parameters, auth=auth):
        if not isinstance(issue, dict):
            problems.append(issue)
            continue

        created = get_datetime(issue['created_at'])
        if not isinstance(issue, dict):
            problems.append(issue)
            continue

        if ((end_date and created > end_date)
                or (start_date and created < start_date)):
            break

        issues.update([state])

    return issues, problems


def get_old_issues(
        owner, repo, start_date=None,
        end_date=None, branch=None, state='open', now=None, auth=None):
    if not now:
        now = datetime.utcnow()

    old_issues = Counter()
    problems = []
    type_api = 'issues'
    parameters = {'sort': 'created', 'direction': 'desc',
                  'filter': 'all', 'state': state}

    if branch:
        parameters['base'] = branch

    for issue in generator_response_from_api_github(
            owner, repo, type_api, parameters, auth=auth):
        if not isinstance(issue, dict):
            problems.append(issue)
            continue

        created = get_datetime(issue['created_at'])

        if ((end_date and created > end_date)
                or (start_date and created < start_date)):
            break

        delta_days = (now - created).days

        if delta_days > DAYS_OLD_ISSUES:
            old_issues.update(['old'])

    return old_issues, problems


def read_config(config_file):
    config = None

    try:
        with open(config_file) as json_data_file:
            config = json.load(json_data_file)
    except FileNotFoundError:
        logging.error(f'Not find configuration file "{config_file}".')

    return config


def get_auth(config):
    auth = None

    if config and 'user' in config and 'password' in config:
        auth = b64encode(
            f"{config['user']}:{config['password']}".encode()
        ).decode("ascii")

    return auth


def main():
    args = get_arguments()
    url = args.url
    date_format = args.date_format
    start_date = get_start_date(args.start_date, date_format)
    end_date = get_end_date(args.end_date, date_format)
    branch = args.branch
    now = datetime.utcnow()
    config = read_config(CONFIG_FILE)
    auth = get_auth(config)
    owner, repo = get_data_from_url(url)

    active_users, problems = get_active_users(
        owner, repo, start_date=start_date, end_date=end_date,
        branch=branch, auth=auth)
    print_active_users(active_users, problems)

    pulls_open, problems = get_pulls(
        owner, repo, start_date=start_date, end_date=end_date,
        branch=branch, auth=auth)
    str_problems = f";Problems: {';'.join(problems)}." if problems else ''
    print(f"Open pull requests;{pulls_open['open']}{str_problems}")

    pulls_closed, problems = get_pulls(
        owner, repo, start_date=start_date, end_date=end_date,
        branch=branch, state='closed', auth=auth)
    str_problems = f";Problems: {';'.join(problems)}." if problems else ''
    print(f"Closed pull requests;{pulls_closed['closed']}{str_problems}")

    old_pulls, problems = get_old_pulls(
        owner, repo, start_date=start_date, end_date=end_date,
        branch=branch, now=now, auth=auth)
    str_problems = f";Problems: {';'.join(problems)}." if problems else ''
    print(f"Old pull requests;{old_pulls['old']}{str_problems}")

    issues_open, problems = get_issues(
        owner, repo, start_date=start_date, end_date=end_date,
        branch=branch, auth=auth)
    str_problems = f";Problems: {';'.join(problems)}." if problems else ''
    print(f"Open issues;{issues_open['open']}{str_problems}")

    issues_closed, problems = get_issues(
        owner, repo, start_date=start_date, end_date=end_date,
        branch=branch, state='closed', auth=auth)
    str_problems = f";Problems: {';'.join(problems)}." if problems else ''
    print(f"Closed issues;{issues_closed['open']}{str_problems}")

    old_issues, problems = get_old_issues(
        owner, repo, start_date=start_date, end_date=end_date,
        branch=branch, now=now, auth=auth)
    str_problems = f";Problems: {';'.join(problems)}." if problems else ''
    print(f"Old issues;{old_issues['old']}{str_problems}")


if __name__ == '__main__':
    main()
