#!/usr/bin/python
#coding: utf-8

__author__ = 'marvyn'
import os, urllib2, requests, smtplib, sys, time
from bs4 import BeautifulSoup
from email.mime.text import MIMEText

url = 'http://www.economist.com/printedition'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/600.3.18 (KHTML, like Gecko) Version/8.0.3 Safari/600.3.18'}

req = urllib2.Request(url = url, headers = headers)
page = urllib2.urlopen(req).read()
soup = BeautifulSoup(page)

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

section_ids = ['section-93', 'section-69', 'section-68', 'section-104', 'section-71', 'section-72', 'section-73', 'section-77729', 'section-99', 'section-75', 'section-76', 'section-74', 'section-77', 'section-79', 'section-80', 'section-89']


if not os.path.isfile('eco_printed_sent_log.txt'):
	log_creat = open('eco_printed_sent_log.txt', 'w')
	log_creat.write('')
	log_creat.close()

sent_article_id = open('eco_printed_sent_log.txt').readlines()

smtp = smtplib.SMTP_SSL()
smtp.connect(mail_config['server'])
smtp.login(mail_config['username'], mail_config['pwd'])


with open('eco_printed_sent_log.txt', 'a') as logfile:
	for item in section_ids:
		section = soup.find(id = item)
		article_list = section.find_all('a', 'node-link')
		item_id = section_ids.index(item) + 1
		with open('eco_print_article_list.txt','a') as result:
			i = 0
			while i < len(article_list):
				article_title = article_list[i].get_text()
				article_href = article_list[i]['href']
				article_id = article_href.split('/')[-1].split('-')[0] + '\n'
				article_link = 'http://www.economist.com' + article_list[i]['href'] + '\n'
				if article_id in sent_article_id:
					print '<%s> already exists!' % article_title
				else:
					logfile.write(article_id)
					result.write(article_link)
					print '<%s> got noted.' % article_title
					msg = MIMEText(article_link, 'plain', 'utf-8')
					msg['Subject'] = article_title
					msg['From'] = mail_config['from']
					msg['To'] = mail_config['to']
					smtp.sendmail(mail_config['from'], mail_config['to'], msg.as_string())
					print '<' + article_title + '> sent successful! (' + str(i + 1) + '/' + str(len(article_list)) + ') (' + str(item_id) + '/' + str(len(section_ids)) + ')'
				i += 1
				time.sleep(1)
smtp.quit()