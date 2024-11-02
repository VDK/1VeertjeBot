#!/usr/bin/python
# -*- coding: utf-8-sig -*-
import requests
import csv
import feedparser
import json
import pywikibot
import time
import re
from googleapiclient.discovery import build


class VeertjeBot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self, config_file="config.json"):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.wd = pywikibot.Site('wikidata', 'wikidata')
        self.wd.login()
        self.wd = self.wd.data_repository()
        self.youtube_channels = self.load_youtube_channels()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Initialize YouTube API client with the loaded API key
        self.youtube = build('youtube', 'v3', developerKey=config['youtube_api_key'])

        # Load author info from the config
        self.author_info = config['author_info']

    def run(self):
        """
        Starts the robot.
        """
        
        cc_contributions = feedparser.parse("https://commons.wikimedia.org/w/api.php?action=feedcontributions&user=1Veertje&newonly=1&namespace=6&feedformat=atom")
        for entity in cc_contributions.entries:
            page = pywikibot.FilePage(self.site,  entity['title'])
            pywikibot.output(page.title())
            if "[[User:1Veertje|1Veertje]]" in page.text:
                pywikibot.output(entity['title'])
                match = re.findall(r"\{\{[a-z]{2}\|1=\s*([A-Za-z0-9_\-]{11})\s*\}\}", page.text)
                if match is not None and len(match) == 1:
                    pywikibot.output('YouTube description loading')
                    self.getYTdescription(page, match[0])
                else:
                    self.changeAuthor(page)
                    self.currentProject(page)
                self.setImageInWD(page)
                self.addCatBasedOnDepicts(page)
            elif page.title().endswith(".webm"):
                self.categorizeVideos(page)
                
    def load_youtube_channels(self, csv_file="youtube_channels.csv"):
        # Dictionary to hold data from the CSV file
        youtube_channels = {}
    
        try:
            # Open the CSV file with UTF-8 encoding and ; separator
            with open(csv_file, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                
                # Load each row of the CSV into the dictionary
                for row in reader:
                    # Assuming 'channel_id', 'title', and 'username' as headers in CSV file
                    channel_id = row.get('channel_id')
                    title = row.get('title')
                    username = row.get('username')
    
                    # Only add valid entries
                    if channel_id and title and username:
                        youtube_channels[channel_id] = {
                            "title": title,
                            "username": username
                        }
            
            print("YouTube channel data loaded successfully.")
        except FileNotFoundError:
            print(f"File {csv_file} not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
    
        return youtube_channels
    
    
    def removeClaim(self, currentstatements, p_id):
        if not currentstatements.get(p_id):
            return
        pywikibot.output('Removing old creator claim', p_id)
        oldclaim = currentstatements.get(p_id)[0].get('id')
        token = self.site.tokens['csrf']
        postdata = {'action' : 'wbremoveclaims',
                    'format' : 'json',
                    'claim' :  oldclaim,
                    'token' : token,
                    'summary' : "remove existing creator statement",
                    'bot' : True,
                    }
        request = self.site.simple_request(**postdata)
        try:
            data = request.submit()
            # Always touch the page to flush it
            # filepage.touch()
        except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
            pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
            # Print the offending token
            time.sleep(30)
            # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
            self. site.tokens.load_tokens(['csrf'])
            # This should be a new token
            print (self.site.tokens['csrf'])
            
    def changeAuthor(self, page):
        page.text = page.text.replace("[[User:1Veertje|1Veertje]]", "[[User:1Veertje|Vera de Kok]]")
        page.text += "\n[[Category:Photographs by User:1Veertje]]"
        page.save(u"Updating author name string and adding [[Category:Photographs by User:1Veertje]]")

        currentdata = self.getCurrentMediaInfo('M' + str(page.pageid))
        currentstatements = currentdata.get('statements')
        if currentstatements:
            self.removeClaim(currentstatements, "P170")
       

        claims = []
        claims.append(self.author_info )
        itemdata = {'claims' : claims}

        token = self.site.tokens['csrf']
        postdata = {'action' : 'wbeditentity',
                    'format' : 'json',
                    'id' :  'M' + str(page.pageid),
                    'data' : json.dumps(itemdata),
                    'token' : token,
                    'summary' : "Add SDC creator information",
                    'bot' : True,
                    }
        #print (json.dumps(postdata, sort_keys=True, indent=4))
        request = self.site.simple_request(**postdata)
        try:
            data = request.submit()
            # Always touch the page to flush it
            # filepage.touch()
            
        except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
            pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
            # Print the offending token
            print (token)
            time.sleep(30)
            # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
            self. site.tokens.load_tokens(['csrf'])
            # This should be a new token
            print (self.site.tokens['csrf'])
    
    def currentProject(self, page):
        f = open('current_project.txt','r')
        contents = f.read().strip()
        if contents != "" and page.text.find(contents) == -1:
            page.text += "\n"+contents
            
            page.text = re.sub(r'\{\{Uncategorized.+?\}\}', '' , page.text )
            page.save("adding " + contents)
        

                
    def getYTdescription(self, page, video_id):
     
    
        # Fetch video details using the YouTube Data API
        try:
            request = self.youtube.videos().list(part='snippet', id=video_id)
            response = request.execute()
    
            if not response['items']:
                print("Video not found.")
                return
    
            snippet = response['items'][0]['snippet']
            title = snippet.get('title', 'Unknown Title')
            description = snippet.get('description', 'No description available')
            publish_date = snippet.get('publishedAt', 'Unknown Date')[:10]  # Format YYYY-MM-DD
            author = snippet.get('channelTitle', 'Unknown Author')
            language = snippet.get('defaultAudioLanguage', None)  # Fetch video language if available
            channel_url = f"https://www.youtube.com/channel/{snippet.get('channelId', '')}"
            
    
            # Format the wikitext with all required information
            wikitext = '''== {{int:filedesc}} ==
{{Information
 |description = %(description)s
 |date = %(date)s
 |source ={{From YouTube|1= %(video_id)s |2= %(title)s }}
 |author = [%(channel_url)s %(author)s]
 |permission = 
 |other versions = 
}}

== {{int:license-header}} ==
{{YouTube CC-BY|%(author)s}}
{{YouTubeReview}}''' % {
                "description": self.lang_label(language, self.cleanWikiText(description)),
                "video_id": video_id,
                "title": self.cleanWikiText(title),
                "author": author,
                "channel_url": channel_url,
                "date": publish_date
            }
    
            # Custom handling for re:publica videos
            if channel_url == 'https://www.youtube.com/channel/UC2p_as5NqbGc9jaSQFsBT-g':
                wikitext = wikitext.replace("{{YouTube CC-BY|re:publica}}", "{{cc-by-sa-4.0|re:publica}}")
    
            # Replace the description section on the page with wikitext and save
            page.text = re.sub(r"== \{\{int:filedesc\}\} ==[^$]+\{\{self\|cc-by-sa-4.0\}\}", wikitext, page.text)
            page.save("Fix source information to YouTube")
    
            # Remove specific structured data claims if they exist
            currentdata = self.getCurrentMediaInfo(f'M{page.pageid}')
            currentstatements = currentdata.get('statements')
            if currentstatements:
                for claim_id in ["P170", "P275", "P7482", "P571"]:
                    self.removeClaim(currentstatements, claim_id)

        except Exception as e:
            print(f"An error occurred while accessing YouTube data: {e}")
        
    def lang_label(self, lang, text):
        if lang is None:
            return text
        return f"{{{{{lang}|{text}}}}}"
                 
            
    def cleanWikiText(self, text):
        text = text.replace("|", "{{!}}")
        text = text.replace("<br>", "")
        text = re.sub(r"https:\/\/youtu\.be\/[A-Za-z0-9_\-]{11}", "", text)
        text = re.sub(r"^• ", "* ", text)
        text = text.replace(
"""Meer nieuws uit de gemeenten Berg en Dal, Beuningen, Druten, Heumen, Mook en Middelaar, Nijmegen, Overbetuwe, West Maas en Waal en Wijchen? Kijk op http://RN7.nl.  

Volg ons ook op: 

* Instagram: RN7online
* Facebook: RN7online
* X: RN7online
* Website: http://www.rn7.nl

#RN7 #Nieuws #Streekomroep""",  "")
        return text
        

           
                
    def setImageInWD(self, page):
        
        people = []
        currentdata = self.getCurrentMediaInfo('M' + str(page.pageid))
        currentstatements = currentdata.get('statements')
        if currentstatements and currentstatements.get('P180'):
            for depicts in currentstatements.get('P180'):
                item = pywikibot.ItemPage(self.wd, depicts.get('mainsnak').get('datavalue').get('value').get('id'))
                item_dict = item.get()
                if item_dict["claims"]["P31"][0].getTarget().id == 'Q5':
                    people.append(item)
        if len(people) == 1:
            item_dict = people[0].get()
            if "P18" not in item_dict["claims"]:
                claim = pywikibot.Claim(self.wd, u'P18') 
                claim.setTarget(page)
                people[0].addClaim(claim, summary=u'Adding new photo')
                    
    def addCatBasedOnDepicts(self, page):
        currentdata = self.getCurrentMediaInfo('M' + str(page.pageid))
        if currentdata.get('statements') and currentdata.get('statements').get('P180'):
            for depicts in currentdata.get('statements').get('P180'):
                item = pywikibot.ItemPage(self.wd, depicts.get('mainsnak').get('datavalue').get('value').get('id'))
                item.get()
                clink = item.sitelinks.get('commonswiki')
                pywikibot.output(clink.title + " found")
                if clink is not None and clink.namespace == ":Category:" and page.text.find("[[Category:"+clink.title) == -1 :
                    page.text += "\n[[Category:"+clink.title+"]]"
                    page.text = re.sub(r'\{\{Uncategorized.+?\}\}', '' , page.text )
                    page.save("adding [[Category:" + clink.title + "]] based on depicts statement")
                    pywikibot.output("adding [[Category:" + clink.title + "]] based on depicts statement")               
                   
                  

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return it so we can expand on it.
        Otherwise return an empty structure with just <s>claims</>statements in it to start
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: json
            """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M52611909
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M10038
        request = self.site.simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def categorizeVideos(self, page):
        """
        Categorizes videos based on YouTube channel information and publication year.
    
        Args:
            page (pywikibot.Page): The page object representing the video file.
        """
        # Regular expressions to match YouTube channel URLs in external links
        full_channel_url_pattern = re.compile(r'youtube\.com/channel/([A-Za-z0-9_-]+)')
        username_url_pattern = re.compile(r'youtube\.com/@([A-Za-z0-9_-]+)')
        date_pattern = re.compile(r'\|date=(\d{4})-\d{2}-\d{2}')  # Pattern to capture year from "|date=YYYY-MM-DD"
    
        # Search for the YouTube channel ID or username in the page's external links
        youtube_channel_id = None
        youtube_username = None
        
        for link in page.extlinks():
            # Check for both full channel URL and username format
            if match := full_channel_url_pattern.search(link):
                youtube_channel_id = match.group(1)
                break
            elif match := username_url_pattern.search(link):
                youtube_username = match.group(1)
                break
    
        # Determine the channel info based on either channel ID or username
        channel_info = None
        if youtube_channel_id and youtube_channel_id in self.youtube_channels:
            channel_info = self.youtube_channels[youtube_channel_id]
        elif youtube_username:
            channel_info = next((info for cid, info in self.youtube_channels.items() if info["username"] == youtube_username), None)
    
        if not channel_info:
            pywikibot.output(f"No matching YouTube channel data found for page: {page.title()}")
            return
    
        title = channel_info["title"]
    
        # Fetch the publication date from structured data
        currentdata = self.getCurrentMediaInfo(f'M{page.pageid}')
        currentstatements = currentdata.get('statements', {})
    
        # Extract year from publication date if available in structured data
        pubdate_claim = currentstatements.get("P571", [])
        year = None
        if pubdate_claim and "datavalue" in pubdate_claim[0]["mainsnak"]:
            pubdate = pubdate_claim[0]["mainsnak"]["datavalue"]["value"]["time"]
            year = pubdate.split("-")[0].replace("+", "")  # Extract the year
    
        # Fallback: Check wikitext for |date=YYYY-MM-DD pattern if structured data date is missing
        if not year:
            match = date_pattern.search(page.text)
            if match:
                year = match.group(1)
    
        # If no year is found, output a message and exit
        if not year:
            pywikibot.output(f"No publication date found for page: {page.title()}")
            return
            
        # Call createCategory to ensure the category exists
        self.createVideoCategory(title, year)
    
        # Create the category name
        category_name = f"{title} videos in {year}"
    
        # Check if the category already exists on the page
        if f"[[Category:{category_name}]]" not in page.text:
            # Add category to page text
            page.text += f"\n[[Category:{category_name}]]"
            page.save(f"Adding category for {title} videos in {year}")
        else:
            pywikibot.output(f"Category '{category_name}' already exists on page: {page.title()}")
            
    def createVideoCategory(self, title, year):
        """
        Creates a category page if it doesn't already exist, with year formatted as first three digits and last digit separated by a pipe.
    
        Args:
            site (pywikibot.Site): The site where the category is to be created.
            title (str): The title of the category.
            year (str): The year for categorization.
        """
        # Define the category name
        category_name = f"{title} videos in {year}"
        category_page = pywikibot.Category(self.site, category_name)
    
        # Check if the category already exists
        if not category_page.exists():
            # Format the year as "202|4" for "2024"
            year_formatted = f"{year[:3]}|{year[3]}"
            category_content = f"{{{{{title} videos|{year_formatted}}}}}"
            
            # Set text and save the new category page
            category_page.text = category_content
            category_page.save(f"Creating category for {title} videos in {year}")
            pywikibot.output(f"Category '{category_name}' created with content: {category_content}")
        else:
            pywikibot.output(f"Category '{category_name}' already exists.")
        

def main():
    veertjeBot = VeertjeBot()
    veertjeBot.run()

if __name__ == "__main__":
    main()
