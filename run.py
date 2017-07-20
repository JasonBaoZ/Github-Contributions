from lxml import html
import json
import requests

SAMPLE_USER_ID = "JasonBaoZ"

GITHUB_URL = "https://github.com"
USER_URL = "https://api.github.com/users/{}/repos?type=all"
REPO_URL = "https://api.github.com/repos/{}/stats/contributors"


# this is only for one year
def get_total_lines(user):
    repositories = json.loads(requests.get(USER_URL.format(user)).content)
    total_lines = 0
    # Go through every repository a user has contributed to
    for repo in repositories:
        contributions = json.loads(requests.get(REPO_URL.format(repo['full_name'])).content)
        # Go through all contributions on given repository, tallying users contributions
        for contribution in contributions:
            if contribution['author']['login'] == user:
                for week in contribution['weeks']:
                    total_lines += week['a'] - week['d']
    return total_lines


# uses a little bit of webscraping, github does not provide endpoint for this
def get_total_lines_with_breakdown(user):
    repositories = json.loads(requests.get(USER_URL.format(user)).content)
    total_lines = {}
    for repo in repositories[:1]:
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
            file_names = inside_tree.xpath('//div[@id="toc"]/ol[@class="content collapse js-transitionable"]/li/text()')
            code_adds = inside_tree.xpath('/span[@class="diffstat float-right"]/span[@class="text-green"]')
            print(summary_items)
# print("Lines of code in past year:", get_total_lines(SAMPLE_USER_ID))
print(get_total_lines_with_breakdown(SAMPLE_USER_ID))
