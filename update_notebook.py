import nbformat
import json

with open('data_1.ipynb', 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

new_code = """import re
import requests
import json
import os
import google.generativeai as genai
from html2image import Html2Image
from PIL import Image

class LinkedinAutomate:
    def __init__(self, access_token, gemini_api_key):
        self.access_token = access_token
        self.gemini_api_key = gemini_api_key
        # Configure Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'LinkedIn-Version': '202401' # Good practice
        }
        self.user_urn = self.get_user_urn()
        self.hti = Html2Image()

    def get_user_urn(self):
        url = "https://api.linkedin.com/v2/userinfo"
        response = requests.get(url, headers={'Authorization': f'Bearer {self.access_token}'})
        user_info = response.json()
        # Extract sub which maps to person URN
        return f"urn:li:person:{user_info['sub']}"

    def generate_proverbs(self):
        print("Generating proverbs...")
        prompt = "Generate 2 short, inspiring proverbs. Return them separated by a newline, with no other text, numbering, or formatting."
        response = self.model.generate_content(prompt)
        proverbs = [line.strip() for line in response.text.strip().split('\\n') if line.strip()][:2]
        return proverbs

    def create_html_images(self, proverbs):
        print("Creating images from proverbs...")
        image_paths = []
        for i, proverb in enumerate(proverbs):
            html_content = f\"\"\"
            <div style="background-color: white; color: black; width: 800px; height: 400px; 
                        display: flex; align-items: center; justify-content: center; 
                        font-family: Arial, sans-serif; font-size: 40px; text-align: center; 
                        padding: 40px; box-sizing: border-box;">
                {proverb}
            </div>
            \"\"\"
            output_file = f'proverb_{i+1}.png'
            self.hti.screenshot(html_str=html_content, save_as=output_file, size=(800, 400))
            
            # STRIP ALPHA CHANNEL: load with PIL, convert to RGB, and save back as PNG
            # This ensures no transparent background gets rendered as black on LinkedIn or elsewhere.
            with Image.open(output_file) as img:
                rgb_img = img.convert('RGB')
                rgb_img.save(output_file, 'PNG')

            image_paths.append(output_file)
        return image_paths

    def register_image_upload(self):
        url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": self.user_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        upload_url = response_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn = response_data['value']['asset']
        return upload_url, asset_urn

    def upload_local_image(self, upload_url, file_path):
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'image/png'  # Force LinkedIn to perceive this as pure PNG
        }
        response = requests.post(upload_url, data=image_data, headers=headers)
        response.raise_for_status()
        return response.status_code

    def post_images_to_feed(self, asset_urns):
        print("Posting to LinkedIn...")
        url = "https://api.linkedin.com/v2/ugcPosts"
        
        media_items = []
        for urn in asset_urns:
            media_items.append({
                "status": "READY",
                "media": urn
            })

        payload = {
            "author": self.user_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": "Here are some inspiring proverbs for the day! ✨\\n#proverbs #inspiration #dailyquotes"
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": media_items
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def main_func(self):
        proverbs = self.generate_proverbs()
        print(f"Generated Proverbs: {proverbs}")
        
        image_paths = self.create_html_images(proverbs)
        print(f"Generated Images: {image_paths}")
        
        asset_urns = []
        for path in image_paths:
            upload_url, asset_urn = self.register_image_upload()
            print(f"Registered upload for {path}. Uploading...")
            status = self.upload_local_image(upload_url, path)
            print(f"Upload status: {status}")
            asset_urns.append(asset_urn)
            
        print(f"Creating post with assets: {asset_urns}")
        post_response = self.post_images_to_feed(asset_urns)
        print(f"Post Response: {json.dumps(post_response, indent=2)}")

# Read tokens
config_path = 'linked_in_token.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

access_token = config['access_token']
gemini_api_key = config['gemini_api_key']

bot = LinkedinAutomate(access_token, gemini_api_key)
bot.main_func()
"""

# Update the second cell (index 1)
nb.cells[1].source = new_code

with open('data_1.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)
