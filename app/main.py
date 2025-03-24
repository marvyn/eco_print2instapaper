import json
import logging
import os
import smtplib
import time
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from translator import Translator

CURRNET_PATH = os.path.dirname(os.path.abspath(__file__))

# Logging configuration
logging.basicConfig(
    filename=os.path.join(CURRNET_PATH, "logs", "app.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
)


class Config:
    def __init__(self, env_path=None):
        """初始化配置

        Args:
            env_path: .env 文件路径，如果为 None，则使用默认路径
        """
        env_path = os.path.join(CURRNET_PATH, ".env")
        if not os.path.exists(env_path):
            raise FileNotFoundError(f"Configuration file {env_path} not found")
        load_dotenv(env_path)
        self.output_dir = os.path.join(CURRNET_PATH, "output")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.log_dir = os.path.join(CURRNET_PATH, "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.translator = self._setup_translator()

    def _setup_translator(self):
        """设置翻译器"""
        openai_vars = ["OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_MODEL"]
        missing_vars = [var for var in openai_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(
                f"Missing OpenAI environment variables: {', '.join(missing_vars)}"
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        openai_model = os.getenv("OPENAI_MODEL")
        if not openai_model:
            raise ValueError("OPENAI_MODEL environment variable is required")

        return Translator(
            api_key=api_key,
            api_base=os.getenv("OPENAI_API_BASE"),
            model=openai_model,
        )

    @property
    def mail_config(self):
        """获取邮件配置"""
        required_vars = [
            "EMAIL_FROM",
            "EMAIL_SERVER",
            "EMAIL_USERNAME",
            "EMAIL_PASSWORD",
            "EMAIL_TO",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        return {
            "from": os.getenv("EMAIL_FROM"),
            "server": os.getenv("EMAIL_SERVER"),
            "username": os.getenv("EMAIL_USERNAME"),
            "password": os.getenv("EMAIL_PASSWORD"),
            "to": os.getenv("EMAIL_TO"),
        }


def fetch_page(url, headers, max_retries=3, retry_delay=5):
    """获取页面内容，支持重试机制"""
    logging.info(f"Fetching page: {url}")
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            logging.info(f"Successfully fetched page: {url}")
            return response.text
        except requests.RequestException as e:
            logging.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise
    return None


def send_mail(config, subject, content, retry_count=3, is_html=True):
    """发送邮件，支持重试机制"""
    mail_config = config.mail_config

    for attempt in range(retry_count):
        try:
            msg = MIMEText(content, "html" if is_html else "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = mail_config["from"]
            msg["To"] = mail_config["to"]
            with smtplib.SMTP_SSL(mail_config["server"]) as smtp:
                smtp.login(mail_config["username"], mail_config["password"])
                smtp.sendmail(mail_config["from"], mail_config["to"], msg.as_string())
            logging.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logging.error(f"Attempt {attempt + 1}/{retry_count} failed: {e}")
            if attempt < retry_count - 1:
                time.sleep(2)
    return False


class EconomistScraper:
    def __init__(self, config):
        logging.info("Initializing EconomistScraper")
        self.config = config
        self.host = "https://www.economist.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/600.3.18 (KHTML, like Gecko) Version/8.0.3 Safari/600.3.18"
        }
        self.sent_articles = self._load_sent_articles()
        self.eco_print_sent_log_file = os.path.join(
            CURRNET_PATH, "log", "eco_print_sent_log.json"
        )

    def _load_sent_articles(self):
        logging.info("Loading previously sent articles")
        if not os.path.isfile(self.eco_print_sent_log_file):
            logging.info("Creating new sent articles log file")
            with open(self.eco_print_sent_log_file, "w") as f:
                json.dump({}, f)
        with open(self.eco_print_sent_log_file) as f:
            data = json.load(f)
            logging.info(f"Loaded {len(data)} sent articles")
            return data

    def _save_sent_articles(self):
        logging.info(f"Saving {len(self.sent_articles)} sent articles")
        with open(self.eco_print_sent_log_file, "w") as f:
            json.dump(self.sent_articles, f)
        logging.info("Sent articles saved successfully")

    def _extract_articles_by_section(self, soup):
        """将文章按照栏目分类整理"""
        sections = {}
        current_section = None

        for section_header in soup.find_all(
            "h2", class_="title_mb-section-header__title__73sdX"
        ):
            current_section = section_header.get_text().strip()
            sections[current_section] = []

            # 获取当前栏目下的所有文章
            section_div = section_header.find_parent(
                "div", class_="css-12hvk84"
            ) or section_header.find_parent("div", class_="css-ml3cuv")
            if not section_div:
                continue

            teasers = section_div.find_all("div", attrs={"data-test-id": "teaser"})
            for teaser in teasers:
                try:
                    # 提取文章信息
                    headline = teaser.find(
                        "h3", attrs={"data-test-id": "teaser-headline"}
                    )
                    if not headline:
                        continue

                    link = headline.find("a")
                    if not link:
                        continue

                    url = link.get("href")
                    if not url.startswith("http"):
                        url = self.host + url

                    title = link.get_text().strip()

                    # 查找副标题
                    subtitle = teaser.find("p", class_="css-1p38euj")
                    subtitle_text = subtitle.get_text().strip() if subtitle else ""

                    # 查找主题标签
                    topic = teaser.find("p", class_="css-zx0bc2")
                    topic_text = topic.get_text().strip() if topic else ""

                    # 查找图片
                    parent_div = teaser.find_parent("div", class_="css-e3fllv")
                    image_url = None
                    if parent_div:
                        figure = parent_div.find("figure", class_="css-3mn275")
                        if figure:
                            img = figure.find("img")
                            if img and img.get("src"):
                                image_url = img["src"]

                    sections[current_section].append(
                        {
                            "url": url,
                            "title": title,
                            "subtitle": subtitle_text,
                            "topic": topic_text,
                            "image_url": image_url,
                        }
                    )

                except Exception as e:
                    logging.error(f"Error extracting article info: {e}")
                    continue

        return sections

    def _translate_article(self, article):
        """翻译文章的标题和副标题"""
        return self.config.translator.translate_article(article)

    def _generate_html_content(self, sections):
        """生成双语 HTML 格式的邮件内容"""
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                h1 { color: #333; border-bottom: 2px solid #333; }
                h2 { color: #666; margin-top: 20px; }
                .article { margin: 10px 0; padding: 10px; border-bottom: 1px solid #eee; }
                .title { font-weight: bold; color: #000; }
                .subtitle { color: #666; }
                .topic { color: #888; font-style: italic; }
                img { max-width: 300px; height: auto; margin: 10px 0; }
                a { color: #1a0dab; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .translation { color: #444; margin: 5px 0; }
            </style>
        </head>
        <body>
            <h1>The Economist Weekly Edition</h1>
        """

        for section_name, articles in sections.items():
            if not articles:
                continue

            html += f"<h2>{section_name}</h2>"
            for article in articles:
                # 翻译文章内容
                translated = self._translate_article(article)

                html += """
                <div class="article">
                    <div class="title"><a href="{url}">{title}</a></div>
                    <div class="translation">{title_zh}</div>
                    """.format(
                    url=article["url"],
                    title=article["title"],
                    title_zh=translated["title_zh"],
                )

                if article["topic"]:
                    html += f'<div class="topic">{article["topic"]}</div>'
                if article["subtitle"]:
                    html += f'<div class="subtitle">{article["subtitle"]}</div>'
                    html += (
                        f'<div class="translation">{translated["subtitle_zh"]}</div>'
                    )
                if article["image_url"]:
                    html += (
                        f'<img src="{article["image_url"]}" alt="{article["title"]}">'
                    )

                html += "</div>"

        html += """
            </body>
        </html>
        """
        return html

    def _generate_markdown_content(self, sections):
        """生成双语 Markdown 格式的内容"""
        content = "# The Economist Weekly Edition\n\n"
        content += f"Date: {time.strftime('%Y-%m-%d')}\n\n"

        for section_name, articles in sections.items():
            if not articles:
                continue

            content += f"## {section_name}\n\n"
            for article in articles:
                # 翻译文章内容
                translated = self._translate_article(article)

                # 英文标题和链接
                content += f"### [{article['title']}]({article['url']})\n\n"
                # 中文标题
                content += f"### {translated['title_zh']}\n\n"

                if article["topic"]:
                    content += f"**{article['topic']}**\n\n"

                if article["subtitle"]:
                    # 英文副标题
                    content += f"_{article['subtitle']}_\n\n"
                    # 中文副标题
                    content += f"_{translated['subtitle_zh']}_\n\n"

                if article["image_url"]:
                    content += f"![{article['title']}]({article['image_url']})\n\n"

                content += "---\n\n"

        return content

    def _save_markdown_file(self, content):
        """保存 Markdown 文件"""
        filename = f"economist_{time.strftime('%Y%m%d')}.md"
        filepath = os.path.join(self.config.output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logging.info(f"Markdown file saved: {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to save Markdown file: {e}")
            return False

    def process_sections(self):
        """处理整个打印版内容"""
        logging.info("Starting to process print edition")
        try:
            page_content = fetch_page(self.host + "/printedition", self.headers)
            if not page_content:
                logging.error("Failed to fetch print edition page")
                return False

            soup = BeautifulSoup(page_content, "html.parser")
            sections = self._extract_articles_by_section(soup)

            # 生成并保存 Markdown 内容
            markdown_content = self._generate_markdown_content(sections)
            if not self._save_markdown_file(markdown_content):
                logging.warning("Failed to save Markdown content")

            # 继续处理邮件发送
            html_content = self._generate_html_content(sections)
            if send_mail(
                self.config, "The Economist Weekly Edition", html_content, is_html=True
            ):
                logging.info("Successfully sent weekly edition digest")
                # 更新已发送文章记录
                for articles in sections.values():
                    for article in articles:
                        self.sent_articles[article["url"]] = {
                            "title": article["title"],
                            "sent_time": time.time(),
                        }
                self._save_sent_articles()
                return True
            else:
                logging.error("Failed to send weekly edition digest")
                return False

        except Exception as e:
            logging.exception(f"Error processing print edition: {e}")
            return False


def main():
    logging.info("Starting application")
    try:
        config = Config()
        logging.info("Configuration loaded successfully")
        scraper = EconomistScraper(config)
        success = scraper.process_sections()
        if not success:
            logging.error("Failed to process sections")
            return 1
        logging.info("Application completed successfully")
        return 0
    except Exception as e:
        logging.exception(f"Unexpected error occurred: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
