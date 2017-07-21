from collections import defaultdict
from lxml import html
import grequests
import json
import matplotlib.pyplot as plt
import re
import requests
import warnings

GITHUB_URL = "https://github.com"
USER_URL = "https://api.github.com/users/{}/repos?type=all"
REPO_URL = "https://api.github.com/repos/{}/stats/contributors"


# goes through API, may use too many API requests
def get_total_lines(user):
    repositories = json.loads(requests.get(USER_URL.format(user)).content)
    total_lines = 0
    # iterate through every repo
    for repo in repositories:
        contributions = json.loads(requests.get(REPO_URL.format(repo['full_name'])).content)
        # iterate through contributions on repo
        for contribution in contributions:
            if contribution['author']['login'] == user:
                for week in contribution['weeks']:
                    total_lines += week['a'] - week['d']
    return total_lines


# scrapes most data, github does not provide endpoint for this
def get_total_lines_with_breakdown(user):
    repositories = json.loads(requests.get(USER_URL.format(user)).content)
    total_adds = defaultdict(lambda: 0)
    total_deletes = defaultdict(lambda: 0)
    progress = 0
    increment = float(1) / len(repositories)
    repo_commit_requests = (grequests.get(''.join([repo['html_url'], "/commits?author=", user])) for repo in repositories)
    repo_commit_pages = grequests.imap(repo_commit_requests)
    for repo_commit_page in repo_commit_pages:
        print "{}% repositories done".format(progress * 100)
        tree = html.fromstring(repo_commit_page.content)
        commit_urls = tree.xpath('//a[@class="sha btn btn-outline BtnGroup-item"]/@href')
        commit_requests = (grequests.get(''.join([GITHUB_URL, u])) for u in commit_urls)
        commit_request_pages = grequests.imap(commit_requests)
        for commit_request_page in commit_request_pages:
            inside_tree = html.fromstring(commit_request_page.content)
            file_names = inside_tree.xpath('//div[@id="toc"]/ol[@class="content collapse js-transitionable"]/li/a')
            code_adds = inside_tree.xpath('//span[@class="diffstat float-right"]/span[@class="text-green"]/text()')
            code_deletes = inside_tree.xpath('//span[@class="diffstat float-right"]/span[@class="text-red"]/text()')
            # may not be an issue, just a warning
            if len(file_names) != len(code_adds) or len(code_adds) != len(code_deletes):
                warnings.warn("File name, code adds and code deletes may not have lined up correctly")
            offset = 0
            for i in range(len(file_names)):
                # hacky way of handling empty files
                empty_path = inside_tree.xpath('//ol[@class="content collapse js-transitionable"]/li[{}]/span[@class="diffstat float-right"]/a[@class="tooltipped tooltipped-w"]/text()'.format(i + 1))
                if len(empty_path) > 0:
                    offset += 1
                    continue

                file_type = file_names[i].text[file_names[i].text.rfind(".") + 1:]
                total_adds[file_type] += int(re.sub('[^0-9]', '', code_adds[i - offset]))
                total_deletes[file_type] += int(re.sub('[^0-9]', '', code_deletes[i - offset]))
        progress += increment
    return total_adds, total_deletes


def graph_lines_written(code_dict, title="Code changes in past year"):
    labels = ["{} ({} lines)".format(key, code_dict[key]) for key in code_dict.keys()]
    sizes = code_dict.values()
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.1,
                     box.width, box.height * 0.9])
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
              fancybox=True)
    ax.axis("equal")
    plt.title(title)
    plt.show()
