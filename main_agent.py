import os
import json
import requests
import agentql
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

class YouTubeAnalyzer:
    def __init__(self):
        self.agentql_key = os.getenv('AGENTQL_API_KEY')
        self.grok_key = os.getenv('XAI_API_KEY')
        
        if not self.agentql_key or not self.grok_key:
            raise ValueError("Missing required API keys in .env file")
        
        # Initialize AgentQL
        agentql.configure(api_key=self.agentql_key)
        
        self.grok_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.grok_key}"
        }

    def scrape_youtube_data(self, video_url):
        """Scrape YouTube video data using AgentQL and Playwright"""
        
        query = """
        {
            video {
                title
                views
                likes
                upload_date
                channel {
                    name
                    subscriber_count
                }
                description
                comments[] {
                    text
                    likes
                    author
                    date
                }
                tags[]
            }
        }
        """
        
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = agentql.wrap(browser.new_page())
                
                # Navigate to the YouTube video
                print("Navigating to video...")
                page.goto(video_url)
                
                # Wait for main video elements to load
                page.wait_for_selector('ytd-watch-metadata')
                
                # Execute the query
                print("Extracting video data...")
                response = page.query_data(query)
                
                browser.close()
                return response
                
        except Exception as e:
            return f"Error scraping YouTube data: {str(e)}"

    def format_with_grok(self, data):
        """Use Grok to format the data in markdown"""
        
        system_message = """You are a data formatting expert. 
        Convert the provided YouTube video data into a well-structured markdown format.
        Create sections for:
        - Video Title and Basic Info
        - Channel Information
        - Engagement Metrics
        - Video Description
        - Top Comments
        - Tags
        
        Use proper markdown formatting with headers, lists, and tables where appropriate."""
        
        prompt = f"Format this YouTube video data into a comprehensive markdown report: {json.dumps(data, indent=2)}"
        
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "grok-beta",
            "stream": False,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=self.grok_headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            return f"Error formatting data with Grok: {str(e)}"

    def analyze_video(self, video_url):
        """Main method to analyze a YouTube video"""
        
        print(" Starting YouTube video analysis...")
        video_data = self.scrape_youtube_data(video_url)
        
        if isinstance(video_data, str) and "Error" in video_data:
            return video_data
            
        print("✨ Formatting analysis with Grok...")
        formatted_analysis = self.format_with_grok(video_data)
        
        return formatted_analysis

def main():
    video_url = "https://www.youtube.com/watch?v=S520UXpy7r4&list=RDS520UXpy7r4&start_radio=1"
    
    try:
        analyzer = YouTubeAnalyzer()
        result = analyzer.analyze_video(video_url)
        
        # Save the analysis to a markdown file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"youtube_analysis_{timestamp}.md"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result)
            
        print(f"\n✅ Analysis complete! Results saved to {filename}")
        print("\nAnalysis Result:")
        print("-" * 50)
        print(result)
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()
