from collections import defaultdict
from lxml import html
import json
import matplotlib.pyplot as plt
import re
import requests
import warnings

###########
# Edit Here
###########

SAMPLE_USER_ID = "JasonBaoZ"

#### End Edit

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
    for repo in repositories:
        print "{}% repositories done".format(progress * 100)
        scrape_url = ''.join([repo['html_url'], "/commits?author=", user])
        scraped_page = requests.get(scrape_url)
        tree = html.fromstring(scraped_page.content)
        commit_urls = tree.xpath('//a[@class="sha btn btn-outline BtnGroup-item"]/@href')
        for url in commit_urls:
            url = ''.join([GITHUB_URL, url])

            # This is a really bad bottleneck, if there is a link with a better summary of additions
            # and deletions that would be really useful
            inside_page = requests.get(url)
            inside_tree = html.fromstring(inside_page.content)
            file_names = inside_tree.xpath('//div[@id="toc"]/ol[@class="content collapse js-transitionable"]/li/a')
            code_adds = inside_tree.xpath('//span[@class="diffstat float-right"]/span[@class="text-green"]/text()')
            code_deletes = inside_tree.xpath('//span[@class="diffstat float-right"]/span[@class="text-red"]/text()')
            # may not be an issue, just a warning
            if len(file_names) != len(code_adds) or len(code_adds) != len(code_deletes):
                warnings.warn("File name, code adds and code deletes may not have lined up correctly")

            for i in range(len(file_names)):
                # hacky way of handling empty files
                if int(file_names[i].parentNode.children[0].children[0].text) == 0:
                    print(url)
                    continue
                file_type = file_names[i].text[file_names[i].text.rfind(".") + 1 :]
                total_adds[file_type] += int(re.sub('[^0-9]', '', code_adds[i]))
                total_deletes[file_type] += int(re.sub('[^0-9]', '', code_deletes[i]))
        progress += increment
    return total_adds, total_deletes


def graph_lines_written(code_dict):
    labels = ["{} ({} lines)".format(key, code_dict[key]) for key in code_dict.keys()]
    sizes = code_dict.values()
    fig1, ax1 = plt.subplots()
    pie = ax1.pie(sizes, autopct='%1.1f%%')
    plt.legend(pie[0], labels, bbox_to_anchor=(1,0), loc="lower right",
               bbox_transform=plt.gcf().transFigure)
    ax1.axis("equal")
    plt.show()

# print("Lines of code in past year:", get_total_lines(SAMPLE_USER_ID))
total_adds, total_deletes = get_total_lines_with_breakdown(SAMPLE_USER_ID)
graph_lines_written(total_adds)
