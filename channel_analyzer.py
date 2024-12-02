import os
import json
import requests
import agentql
import pandas as pd
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from dateutil.relativedelta import relativedelta

# Load environment variables
load_dotenv()

class YouTubeChannelAnalyzer:
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

    def scrape_channel_videos(self, channel_url):
        """Scrape all videos from a YouTube channel"""
        
        query = """
        {
            channel {
                name
                subscriber_count
                videos[] {
                    title
                    url
                    views
                    likes
                    upload_date
                    duration
                    description
                }
            }
        }
        """
        
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    args=['--disable-dev-shm-usage']
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                )
                page = agentql.wrap(context.new_page())
                
                print(f"Navigating to channel: {channel_url}")
                page.goto(channel_url, wait_until='networkidle')
                
                # Wait for any of these selectors to be visible
                selectors = [
                    "#content",
                    "ytd-channel-content",
                    "#channel-content",
                    "#contents"
                ]
                
                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, timeout=60000)
                        print(f"Found selector: {selector}")
                        break
                    except:
                        continue
                
                # Additional wait to ensure content is loaded
                page.wait_for_timeout(5000)
                
                # Scroll to load more videos
                for i in range(5):
                    print(f"Scrolling iteration {i+1}/5...")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                    
                    # Check if new content has loaded
                    try:
                        page.wait_for_function("""
                            () => {
                                const videos = document.querySelectorAll('ytd-grid-video-renderer');
                                return videos.length > 0;
                            }
                        """, timeout=5000)
                    except:
                        print("No new videos loaded, continuing...")
                
                print("Extracting channel data...")
                response = page.query_data(query)
                
                context.close()
                browser.close()
                return response
                
        except Exception as e:
            print(f"Detailed error: {str(e)}")
            return f"Error scraping channel data: {str(e)}"

    def analyze_channel_data(self, data):
        """Analyze channel data and create visualizations"""
        
        videos_df = pd.DataFrame(data['channel']['videos'])
        
        # Convert views and likes to numeric by extracting numbers only
        def extract_numbers(text):
            if isinstance(text, str):
                return ''.join(filter(str.isdigit, text.split()[0].replace(',', '')))
            return text

        # Convert relative dates to absolute dates
        def convert_relative_date(text):
            if isinstance(text, str):
                if "قبل" in text:
                    parts = text.split()
                    number = int(parts[1])
                    unit = parts[2]
                    
                    if "سنة" in unit or "سنوات" in unit:
                        return datetime.now() - relativedelta(years=number)
                    elif "شهر" in unit or "أشهر" in unit:
                        return datetime.now() - relativedelta(months=number)
                    elif "يوم" in unit or "أيام" in unit:
                        return datetime.now() - relativedelta(days=number)
            return text

        # Clean and convert views and likes
        videos_df['views'] = videos_df['views'].apply(extract_numbers)
        videos_df['likes'] = videos_df['likes'].apply(extract_numbers)
        
        # Convert to numeric, replacing any empty strings with 0
        videos_df['views'] = pd.to_numeric(videos_df['views'], errors='coerce').fillna(0)
        videos_df['likes'] = pd.to_numeric(videos_df['likes'], errors='coerce').fillna(0)
        
        # Convert upload_date to datetime
        videos_df['upload_date'] = videos_df['upload_date'].apply(convert_relative_date)
        videos_df['upload_date'] = pd.to_datetime(videos_df['upload_date'], errors='coerce')
        
        # Convert numpy types to Python native types for JSON serialization
        analysis = {
            'channel_name': data['channel']['name'],
            'total_videos': int(len(videos_df)),
            'total_views': int(videos_df['views'].sum()),
            'average_views': float(videos_df['views'].mean()),
            'most_viewed': [
                {
                    'title': row['title'],
                    'views': int(row['views']),
                    'url': row['url']
                }
                for _, row in videos_df.nlargest(5, 'views')[['title', 'views', 'url']].iterrows()
            ],
            'least_viewed': [
                {
                    'title': row['title'],
                    'views': int(row['views']),
                    'url': row['url']
                }
                for _, row in videos_df.nsmallest(5, 'views')[['title', 'views', 'url']].iterrows()
            ],
            'most_liked': [
                {
                    'title': row['title'],
                    'likes': int(row['likes']),
                    'url': row['url']
                }
                for _, row in videos_df.nlargest(5, 'likes')[['title', 'likes', 'url']].iterrows()
            ],
            'upload_frequency': float(self._calculate_upload_frequency(videos_df))
        }
        
        # Create visualizations
        self._create_visualizations(videos_df, data['channel']['name'])
        
        return analysis

    def _calculate_upload_frequency(self, df):
        """Calculate average upload frequency"""
        df = df.sort_values('upload_date')
        date_diffs = df['upload_date'].diff().dropna()
        return date_diffs.mean().days

    def _create_visualizations(self, df, channel_name):
        """Create and save visualization plots"""
        
        # Set style
        sns.set_style('darkgrid')
        
        # 1. Views distribution
        plt.figure(figsize=(12, 6))
        sns.histplot(data=df, x='views', bins=30)
        plt.title(f'Views Distribution - {channel_name}')
        plt.xlabel('Views')
        plt.ylabel('Count')
        plt.savefig('views_distribution.png')
        plt.close()
        
        # 2. Views vs Likes scatter plot
        plt.figure(figsize=(12, 6))
        sns.scatterplot(data=df, x='views', y='likes')
        plt.title(f'Views vs Likes - {channel_name}')
        plt.xlabel('Views')
        plt.ylabel('Likes')
        plt.savefig('views_vs_likes.png')
        plt.close()
        
        # 3. Upload timeline
        plt.figure(figsize=(15, 6))
        timeline = df.set_index('upload_date')['views'].plot(kind='line')
        plt.title(f'Upload Timeline and Views - {channel_name}')
        plt.xlabel('Upload Date')
        plt.ylabel('Views')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('upload_timeline.png')
        plt.close()

    def format_analysis_with_grok(self, analysis):
        """Format the analysis using Grok"""
        
        system_message = """You are a YouTube channel analysis expert.
        Create a comprehensive markdown report from the provided channel analysis data.
        Include sections for:
        - Channel Overview
        - Top Performing Videos
        - Underperforming Videos
        - Upload Frequency Analysis
        - Engagement Metrics
        
        Make the report insightful and actionable for content creators."""
        
        prompt = f"Create a detailed channel analysis report from this data: {json.dumps(analysis, indent=2)}"
        
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
            return f"Error formatting analysis with Grok: {str(e)}"

    def analyze_channel(self, channel_url):
        """Main method to analyze a YouTube channel"""
        
        print(" Starting channel analysis...")
        channel_data = self.scrape_channel_videos(channel_url)
        
        if isinstance(channel_data, str) and "Error" in channel_data:
            return channel_data
        
        print("📊 Analyzing channel data...")
        analysis = self.analyze_channel_data(channel_data)
        
        print("✨ Formatting analysis with Grok...")
        formatted_analysis = self.format_analysis_with_grok(analysis)
        
        return formatted_analysis

def main():
    # Replace this URL with any YouTube channel you want to analyze
    channel_url = "https://www.youtube.com/@bechirmathlouthi3419"

    
    try:
        analyzer = YouTubeChannelAnalyzer()
        result = analyzer.analyze_channel(channel_url)
        
        # Save the analysis to a markdown file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"channel_analysis_{timestamp}.md"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result)
            
        print(f"\n✅ Channel analysis complete! Results saved to {filename}")
        print("\nAnalysis Result:")
        print("-" * 50)
        print(result)
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")

if __name__ == "__main__":
    main() 