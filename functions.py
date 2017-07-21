from collections import defaultdict
from lxml import html
import grequests
import json
import matplotlib.pyplot as plt
import re
import requests
import warnings


class Contributions:

    GITHUB_URL = 'https://github.com'
    USER_URL = 'https://api.github.com/users/{}/repos?type=all'
    REPO_URL = 'https://api.github.com/repos/{}/stats/contributors'

    def __init__(self, user, file_types=[]):
        self.user = user
        if file_types:
            self._file_types = file_types

    @property
    def file_types(self):
        return self._file_types

    @file_types.setter
    def file_types(self, value):
        self._file_types = value
        # if we change the file types, then total_adds and total_deletes should be gone
        del self.total_adds
        del self.total_deletes

    # goes through API, may use too many API requests
    def get_total_lines(self):
        repositories = json.loads(requests.get(self.USER_URL.format(self.user)).content)
        total_lines = 0
        # iterate through every repo
        for repo in repositories:
            contributions = json.loads(requests.get(self.REPO_URL.format(repo['full_name'])).content)
            # iterate through contributions on repo
            for contribution in contributions:
                if contribution['author']['login'] == self.user:
                    for week in contribution['weeks']:
                        total_lines += week['a'] - week['d']
        return total_lines

    # scrapes most data, github does not provide endpoint for this
    def get_total_lines_with_breakdown(self):
        # get a list of all the repositories a user contributes to
        repositories = json.loads(requests.get(self.USER_URL.format(self.user)).content)
        total_adds = defaultdict(lambda: 0)
        total_deletes = defaultdict(lambda: 0)
        progress = 0
        increment = float(1) / len(repositories)

        # look into performance on this, does not seem to be doing what I think it is doing
        repo_commit_requests = (grequests.get(''.join([repo['html_url'], '/commits?author=', self.user])) for repo in repositories)
        repo_commit_pages = grequests.imap(repo_commit_requests)
        for repo_commit_page in repo_commit_pages:
            # primitive way of saying don't give up on me
            print '{}% repositories done'.format(progress * 100)
            tree = html.fromstring(repo_commit_page.content)
            commit_urls = tree.xpath('//a[@class="sha btn btn-outline BtnGroup-item"]/@href')

            commit_requests = (grequests.get(''.join([self.GITHUB_URL, u])) for u in commit_urls)
            commit_request_pages = grequests.imap(commit_requests)

            for commit_request_page in commit_request_pages:
                inside_tree = html.fromstring(commit_request_page.content)

                file_names = inside_tree.xpath('//div[@id="toc"]/ol[@class="content collapse js-transitionable"]/li/a')
                code_adds = inside_tree.xpath('//span[@class="diffstat float-right"]/span[@class="text-green"]/text()')
                code_deletes = inside_tree.xpath('//span[@class="diffstat float-right"]/span[@class="text-red"]/text()')

                # may not be an issue, just a warning
                if len(file_names) != len(code_adds) or len(code_adds) != len(code_deletes):
                    warnings.warn('File name, code adds and code deletes may not have lined up correctly')

                offset = 0
                for i in range(len(file_names)):
                    # hacky way of handling empty files
                    empty_path = inside_tree.xpath('//ol[@class="content collapse js-transitionable"]/li[{}]/span[@class="diffstat float-right"]/a[@class="tooltipped tooltipped-w"]/text()'.format(i + 1))
                    if len(empty_path) > 0:
                        offset += 1
                        continue
                    file_type = file_names[i].text[file_names[i].text.rfind('.') + 1:]
                    if not hasattr(self, 'file_types') or file_type in self.file_types:
                        total_adds[file_type] += int(re.sub('[^0-9]', '', code_adds[i - offset]))
                        total_deletes[file_type] += int(re.sub('[^0-9]', '', code_deletes[i - offset]))

            progress += increment

        self.total_adds = total_adds
        self.total_deletes = total_deletes
        return total_adds, total_deletes

    def graph_lines_written(self, code_dict, title='Code changes in past year'):
        labels = ['{} ({} lines)'.format(key, code_dict[key]) for key in code_dict.keys()]
        sizes = code_dict.values()
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels)
        box = ax.get_position()
        ax.set_position([box.x0, box.y0 + box.height * 0.1,
                         box.width, box.height * 0.9])
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
                  fancybox=True)
        ax.axis('equal')
        plt.title(title)
        plt.show()

    def graph_all(self, total_adds=None, total_deletes=None):
        if total_adds and total_deletes:
            self.graph_lines_written(total_adds, 'Total Lines added in the last year')
            self.graph_lines_written(total_deletes, 'Total Lines deleted in the last year')
            return
        if hasattr(self, 'total_adds') and hasattr(self, 'total_deletes'):
            self.graph_lines_written(self.total_adds, 'Total Lines added in the last year')
            self.graph_lines_written(self.total_deletes, 'Total Lines deleted in the last year')
            return
        self.get_total_lines_with_breakdown()
        self.graph_all()
