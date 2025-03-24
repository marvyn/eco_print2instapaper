#!/usr/bin/python
#coding: utf-8

__author__ = 'marvyn'
import os, json, urllib2, requests, smtplib, sys, time
from bs4 import BeautifulSoup
from email.mime.text import MIMEText

host = 'http://www.economist.com'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/600.3.18 (KHTML, like Gecko) Version/8.0.3 Safari/600.3.18'}

req = urllib2.Request(url = host + '/printedition', headers = headers)
page = urllib2.urlopen(req).read()
soup = BeautifulSoup(page)
article_no = len(soup.find_all('a', 'node-link'))

mail_config = {
    'from': 'xxxxxxxx@qq.com',
    'server': 'smtp.qq.com',
    'username': 'xxxxxxxx@qq.com',
    'pwd': '''xxxxxxxxxxxxxxxx''',
    'to': 'readlater.xxxxxxxxxx@instapaper.com'
}

sections = {
	'The world this week': 'section-93',
	'Leaders': 'section-69',
	'Letters': 'section-68',
	'Briefing': 'section-104',
	'United States': 'section-71',
	'The Americas': 'section-72',
	'Asia': 'section-73',
	'China': 'section-77729',
	'Middle East and Africa': 'section-99',
	'Europe': 'section-75',
	'Britain': 'section-76',
	'International': 'section-74',
	'Business': 'section-77',
	'Finance and economics': 'section-79',
	'Science and technology': 'section-80',
	'Books and arts': 'section-89'
}
sections_res = {'section-71': 'United States', 'section-89': 'Books and arts', 'section-73': 'Asia', 'section-72': 'The Americas', 'section-75': 'Europe', 'section-99': 'Middle East and Africa', 'section-77': 'Business', 'section-76': 'Britain', 'section-80': 'Science and technology', 'section-68': 'Letters', 'section-69': 'Leaders', 'section-93': 'The world this week', 'section-79': 'Finance and economics', 'section-77729': 'China', 'section-104': 'Briefing', 'section-74': 'International'}

section_ids = ['section-93', 'section-69', 'section-68', 'section-104', 'section-71', 'section-72', 'section-73', 'section-77729', 'section-99', 'section-75', 'section-76', 'section-74', 'section-77', 'section-79', 'section-80', 'section-89']


if not os.path.isfile('eco_print_sent_log.json'):
	with open('eco_print_sent_log.json', 'w') as log_creat:
		json.dump({}, log_creat)

def send_mail(subject, content):
	msg = MIMEText(content, 'plain', 'utf-8')
	msg['Subject'] = subject
	msg['From'] = mail_config['from']
	msg['To'] = mail_config['to']
	smtp = smtplib.SMTP_SSL()
	smtp.connect(mail_config['server'])
	smtp.login(mail_config['username'], mail_config['pwd'])
	smtp.sendmail(mail_config['from'], mail_config['to'], msg.as_string())
	smtp.close()

def main():
	sent_article_id = json.load(open('eco_print_sent_log.json'))
	j = 0
	for item in section_ids:
		item_id = section_ids.index(item) + 1
		print '========== Processing section: %s... (%s/16) ==========' % (sections_res[item], item_id)
		section = soup.find(id = item)
		section_title = section.find('h4').get_text()
		section_fly_titles = section.find_all('h5')
		article_list = section.find_all('a', 'node-link')
		i = 0
		while i < len(article_list):
			j += 1
			article_title = article_list[i].get_text()
			if item == 'section-93':
				article_subject= article_title
			else:
				article_subject = section_fly_titles[i].get_text() + ' - ' + article_title
			article_href = article_list[i]['href']
			article_id = article_href.split('/')[-1].split('-')[0]
			article_link = host + article_list[i]['href']
			if article_id in sent_article_id.keys():
				print '[%s/%s] <%s> already exists! (%s/%s)' % (i+1, len(article_list), article_subject, j, article_no)
			else:
				time.sleep(1)
				sent_article_id[article_id] = article_link
				print '<%s> got noted.' % article_subject
				send_mail(article_subject, article_link)
				print '[%s/%s] <%s> sent successful! (%s/%s)' % (i+1, len(article_list), article_subject, j, article_no)
			i += 1
			time.sleep(0.5)
	with open('eco_print_sent_log.json', 'w') as log_creat:
		json.dump(sent_article_id, log_creat)

if __name__ == '__main__':
	main()