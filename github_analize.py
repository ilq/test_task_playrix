import argparse
import datetime
import http.client
import json
from collections import Counter

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
MAX_ACTIVE_USER = 30
DAYS_OLD_PULL = 30
DAYS_OLD_ISSUES = 14
TEST_DATA = False

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--url', dest='url', action='store',
        help=('url репозитория.')
    )
    parser.add_argument(
        '-s', '--start_date', dest='start_date', action='store',
        help=('Дата начала анализа.')
    )
    parser.add_argument(
        '-e', '--end_date', dest='end_date', action='store',
        help=('Дата окончания анализа.')
    )
    parser.add_argument(
        '-f', '--format', dest='date_format', action='store',
        default='%Y-%m-%dT%H:%M:%SZ', help=('Формат даты.')
    )
    parser.add_argument(
        '-b', '--branch', dest='branch', action='store', default='master',
        help=('Ветка репозитория.')
    )
    args = parser.parse_args()
    return args


def get_connection():
    connection = http.client.HTTPSConnection("api.github.com", timeout=5)
    return connection


def get_data_from_url(url):
    root = 'github.com/'

    if root in url:
        url = url.split(root)[1]

    if url[0] == '/':
        url = url[1:]

    owner, repo = url.split('/')[:2]

    return owner, repo

def get_response_from_api_github():
    page = 0
    per_page = 100
    pulls = Counter()
    created = ''
    flag = True
    pass

def get_active_users_response(connection, owner, repo, page=1, per_page=100):
    connection.request('GET',
                       (f'/repos/{owner}/{repo}/commits?'
                        f'page={page}per_page={per_page}'),
                       headers={'User-Agent': USER_AGENT})
    response = json.loads(connection.getresponse().read().decode())
    return response


def get_active_users(connection, owner, repo,
                     start_date=None, end_date=None, branch=None):
    page = 0
    per_page = 100
    active_users = Counter()

    while True:
        page += 1
        print(page)
        # response = get_active_users_response(
        #     connection, owner, repo, page, per_page
        # )
        url = f'/repos/{owner}/{repo}/commits?page={page}&per_page={per_page}'

        if start_date:
            url += f'&since={start_date}'

        if end_date:
            url += f'&until={end_date}'

        if branch:
            url += f'&sha={branch}'

        connection.request('GET', url, headers={'User-Agent': USER_AGENT})
        response = json.loads(connection.getresponse().read().decode())

        if not isinstance(response, list):
            break

        for id, el in enumerate(response):
            if el['author'] and el['author'].get('login', None):
                author = el['author']['login']
                active_users.update([author])

        if len(response) < per_page:
            break

        print(active_users.most_common(5))

    return active_users


def print_active_users(active_users):
    print('|{:*^31}|'.format(''))
    print('|{: ^31}|'.format('Active users'))
    print('|{:*^31}|'.format(''))
    print('|{: ^20}|{: ^10}|'.format('Author', 'Count'))
    print('|{:*^31}|'.format(''))

    for author, count in active_users.most_common(MAX_ACTIVE_USER):
        print('|{: ^20}|{: ^10}|'.format(author, count))

    print('|{:*^31}|'.format(''))


def get_pulls(connection, owner, repo, start_date=None,
              end_date=None, branch=None, state='open'):
    page = 0
    per_page = 100
    pulls = Counter()
    created = ''
    flag = True

    while flag:
        page += 1
        print(page)
        # response = get_active_users_response(
        #     connection, owner, repo, page, per_page
        # )
        url = (f'/repos/{owner}/{repo}/pulls'
               f'?page={page}&per_page={per_page}'
               f'&sort=created&direction=desc')

        if branch:
            url += f'&base={branch}'

        if state:
            url += f'&state={state}'

        print(url)
        connection.request('GET', url, headers={'User-Agent': USER_AGENT})
        response = json.loads(connection.getresponse().read().decode())

        if not isinstance(response, list):
            break

        for idx, el in enumerate(response):
            created = el['created_at']
            if created < start_date:
                flag = False
                break

            pulls.update([state])
            print(created, state)

        if len(response) < per_page:
            break

        # print(pulls)

    return pulls


def print_pulls(pulls):
    print('|{:*^21}|'.format(''))
    print('|{: ^21}|'.format('Pull requests'))
    print('|{:*^21}|'.format(''))
    print('|{: ^10}|{: ^10}|'.format('Open', 'Closed'))
    print('|{:*^21}|'.format(''))
    print('|{: ^10}|{: ^10}|'.format(pulls['open'], pulls['closed']))
    print('|{:*^21}|'.format(''))


def format_github_datetime(created):
    return datetime.datetime.strptime(created, '%Y-%m-%dT%H:%M:%SZ')


def get_old_pulls(connection, owner, repo, start_date=None,
                  end_date=None, branch=None, state='open'):
    page = 0
    per_page = 100
    pulls = Counter()
    created = ''
    flag = True
    now = datetime.datetime.now()

    while flag:
        page += 1
        print(page)
        # response = get_active_users_response(
        #     connection, owner, repo, page, per_page
        # )
        url = (f'/repos/{owner}/{repo}/pulls'
               f'?page={page}&per_page={per_page}'
               f'&sort=created&direction=desc')

        if branch:
            url += f'&base={branch}'

        if state:
            url += f'&state={state}'

        print(url)
        connection.request('GET', url, headers={'User-Agent': USER_AGENT})
        response = json.loads(connection.getresponse().read().decode())

        if not isinstance(response, list):
            break

        for idx, el in enumerate(response):
            created = el['created_at']

            if created < start_date:
                flag = False
                break

            delta_days = (now - format_github_datetime(created)).days

            if delta_days > DAYS_OLD_PULL:
                pulls.update(['old'])

            print(created, state)

        if len(response) < per_page:
            break

    return pulls


def print_old_pulls(old_pulls):
    print('|{:*^21}|'.format(''))
    print('|{: ^21}|'.format('Old pull requests'))
    print('|{:*^21}|'.format(''))
    print('|{: ^21}|'.format(old_pulls['old']))
    print('|{:*^21}|'.format(''))


def get_issues(connection, owner, repo, start_date=None,
              end_date=None, branch=None, state='open'):
    page = 0
    per_page = 100
    counter = Counter()
    created = ''
    flag = True
    while flag:
        page += 1
        print(page)
        # response = get_active_users_response(
        #     connection, owner, repo, page, per_page
        # )
        url = (f'/repos/{owner}/{repo}/issues'
               f'?page={page}&per_page={per_page}'
               f'&filter=all'
               f'&sort=created&direction=desc')

        if branch:
            url += f'&base={branch}'

        if state:
            url += f'&state={state}'

        print(url)
        connection.request('GET', url, headers={'User-Agent': USER_AGENT})
        response = json.loads(connection.getresponse().read().decode())

        if not isinstance(response, list):
            break

        for idx, el in enumerate(response):
            created = el['created_at']
            if created < start_date:
                flag = False
                break

            counter.update([state])
            # print(created, state)

        if len(response) < per_page:
            break

        # print(pulls)

    return counter


def print_issues(issues):
    print('|{:*^21}|'.format(''))
    print('|{: ^21}|'.format('Issues'))
    print('|{:*^21}|'.format(''))
    print('|{: ^10}|{: ^10}|'.format('Open', 'Closed'))
    print('|{:*^21}|'.format(''))
    print('|{: ^10}|{: ^10}|'.format(issues['open'], issues['closed']))
    print('|{:*^21}|'.format(''))


def get_old_issues(connection, owner, repo, start_date=None,
                  end_date=None, branch=None, state='open'):
    page = 0
    per_page = 100
    counter = Counter()
    created = ''
    flag = True
    now = datetime.datetime.now()

    while flag:
        page += 1
        print(page)
        # response = get_active_users_response(
        #     connection, owner, repo, page, per_page
        # )
        url = (f'/repos/{owner}/{repo}/issues'
               f'?page={page}&per_page={per_page}'
               f'&filter=all'
               f'&sort=created&direction=desc')

        if branch:
            url += f'&base={branch}'

        if state:
            url += f'&state={state}'

        print(url)
        connection.request('GET', url, headers={'User-Agent': USER_AGENT})
        response = json.loads(connection.getresponse().read().decode())

        if not isinstance(response, list):
            break

        for idx, el in enumerate(response):
            created = el['created_at']

            if created < start_date:
                flag = False
                break

            delta_days = (now - format_github_datetime(created)).days

            if delta_days > DAYS_OLD_ISSUES:
                counter.update(['old'])

        if len(response) < per_page:
            break

    return counter


def print_old_issues(old_issues):
    print('|{:*^21}|'.format(''))
    print('|{: ^21}|'.format('Old issues'))
    print('|{:*^21}|'.format(''))
    print('|{: ^21}|'.format(old_issues['old']))
    print('|{:*^21}|'.format(''))


def main():
    args = get_arguments()
    url = args.url
    start_date = args.start_date
    end_date = args.end_date
    date_format = args.date_format
    branch = args.branch

    if TEST_DATA:
        url = 'https://github.com/fastlane/fastlane/'
        branch = 'master'
        start_date = '2019-12-30T00:00:00Z'

    connection = get_connection()
    owner, repo = get_data_from_url(url)
    print(owner, repo)
    # active_users = get_active_users(connection, owner, repo,
    #                                 start_date=start_date, end_date=end_date,
    #                                 branch=branch)
    # print_active_users(active_users)
    
    # pulls_open = get_pulls(connection, owner, repo, start_date=start_date,
    #                        end_date=end_date, branch=branch)
    # pulls_closed = get_pulls(connection, owner, repo, start_date=start_date,
    #                          end_date=end_date, branch=branch, state='closed')
    # print_pulls(pulls_open + pulls_closed)
    # old_pulls = get_old_pulls(connection, owner, repo, start_date=start_date,
    #                           end_date=end_date, branch=branch)
    # print_old_pulls(old_pulls)
    # issues_open = get_issues(connection, owner, repo, start_date=start_date,
    #                          end_date=end_date, branch=branch)
    # issues_closed = get_issues(connection, owner, repo, start_date=start_date,
    #                            end_date=end_date, branch=branch, state='closed')
    # print_issues(issues_open + issues_closed)
    old_issues = get_old_issues(connection, owner, repo, start_date=start_date,
                                end_date=end_date, branch=branch)
    print_old_issues(old_issues)


if __name__ == '__main__':
    main()
