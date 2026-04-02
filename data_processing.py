import pandas as pd
from database import get_collection
import uuid
import os
import time
import requests
from gossip import GOSSIP_DATA

CSV_FILE_PATH = "survey_responses.tsv"

RAPIDAPI_KEY = "c680c2f07emshc9b1b35d51860a4p15acc6jsne5dda6456f81"
RAPIDAPI_HOST = "linkedin-data-api.p.rapidapi.com"

LINKEDIN_PROFILES = {
    "Francesco Polimeni": "https://www.linkedin.com/in/francescopolimeni/",
    "Ayush Raj": "https://www.linkedin.com/in/r-ayush-1101/",
    "David Puchala": "https://www.linkedin.com/in/davidpuchala/",
    "Yiben Fruncillo": "https://www.linkedin.com/in/yiben-fruncillo/",
    "Maria París": "https://www.linkedin.com/in/maria-paris-ros/",
    "Sharath Raveendran": "https://www.linkedin.com/in/sharath-raveendran/",
    "Brice Da Costa": "https://www.linkedin.com/in/brice-da-costa/",
    "Gabriela Méndez": "https://www.linkedin.com/in/gabriela-m%C3%A9ndez-637344265/",
    "Miguel de Faria": "https://www.linkedin.com/in/migueldefaria/",
    "Matteo Guardamagna": "https://www.linkedin.com/in/matteoguardamagna/",
    "Lara Isikci": "https://www.linkedin.com/in/lara-isikci/",
    "Fabrizio Iacuzio": "https://www.linkedin.com/in/fabrizio-iacuzio/",
    "Florian Nix": "https://www.linkedin.com/in/florian-nix-933b33241/",
    "Jad Zoghaib": "https://www.linkedin.com/in/jadzoghaib/",
    "María Mora": "https://www.linkedin.com/in/maria-angelica-mora-zamora/",
    "Sean": "https://www.linkedin.com/in/seanhoet/",
    "eng pongtanya": "https://www.linkedin.com/in/pornpisuth-pongtanya-b23b98353/",
    "Ella Magdic": "https://www.linkedin.com/in/ellamagdic/",
    "Omar Trabelsi": "https://www.linkedin.com/in/omar-trabelsi-758831176/",
    "Lucas Haesaert": "https://www.linkedin.com/in/lucas-haesaert/",
    "Hiroaki Nakano": "https://www.linkedin.com/in/hiroaki-nakano-0a26a3352/",
    "Amat Montoto": "https://www.linkedin.com/in/amatmontoto/",
    "Marc Sardà": "https://www.linkedin.com/in/marc-sarda-masriera/",
    "Francesc Cañavate": "https://www.linkedin.com/in/francesc-canavate/",
    "Sara Fibla": "https://www.linkedin.com/in/sara-fibla-salgado-139855329/",
    "Giorgio Fiorentino": "https://www.linkedin.com/in/giorgio-fiorentino/"
}

def get_linkedin_profile_data(linkedin_url):
    """
    Hits the RapidAPI endpoint to extract LinkedIn resume details automatically.
    """
    if not linkedin_url or linkedin_url == "N/A":
        return "No LinkedIn Profile given."
        
    print(f"Scraping LinkedIn data for: {linkedin_url} ...")
    url = "https://linkedin-data-api.p.rapidapi.com/get-profile-data-by-url"
    querystring = {"url": linkedin_url}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            data = response.json()
            
            # The API returns a large JSON object, we will extract the most relevant parts for the RAG agent
            headline = data.get("headline", "Not specified")
            summary = data.get("summary", "No summary")
            location = data.get("location", "Not specified")
            
            profile_details = f"Headline: {headline}\nLocation: {location}\nSummary: {summary}\n"
            
            # Extract top 3 experiences if available
            positions = data.get("position", [])
            if isinstance(positions, list) and len(positions) > 0:
                profile_details += "Experience:\n"
                # Keep it to top 3 so we don't overflow the Agent's token window
                for pos in positions[:3]: 
                    title = pos.get("title", "")
                    company = pos.get("companyName", "")
                    profile_details += f" - {title} at {company}\n"
            
            # Extract top 3 latest educations if available
            education = data.get("education", [])
            if isinstance(education, list) and len(education) > 0:
                profile_details += "Education:\n"
                for edu in education[:3]:
                    school = edu.get("schoolName", "")
                    degree = edu.get("degreeName", "")
                    field = edu.get("fieldOfStudy", "")
                    profile_details += f" - {degree} in {field} from {school}\n"
                    
            return profile_details.strip()
        else:
            return f"Failed to scrape LinkedIn details. API Error Code: {response.status_code}"
    except Exception as e:
        return f"Error scraping LinkedIn profile: {str(e)}"

def process_csv_and_insert():
    try:
        # Load TSV (tab separated) since the provided data uses tabs
        df = pd.read_csv(CSV_FILE_PATH, sep='\t')
    except Exception as e:
        print(f"Error loading {CSV_FILE_PATH}: {e}")
        return
        
    collection = get_collection()
    
    documents = []
    metadatas = []
    ids = []
    
    for index, row in df.iterrows():
        # Get name from the 2nd column
        name_col = "0. Please write your name and surname"
        name = row.get(name_col, f"Person_{index}").strip()
        linkedin_url = LINKEDIN_PROFILES.get(name, "N/A")
        
        # Scrape their LinkedIn live when running the script
        linkedin_scraped_data = get_linkedin_profile_data(linkedin_url)
        
        # Add a 1.5-second break between profiles to respect the RapidAPI FREE tier rate-limits
        time.sleep(1.5)
        
        # --- 1) The Public Profile Chunk ---
        # Putting more "standard" classroom/social facts here
        public_data = f"""
        Name: {name}
        LinkedIn Profile Link: {linkedin_url}
        LinkedIn Scraped Details: 
        {linkedin_scraped_data}
        
        Technical Background: {row.get('11. Do you have a technical background?', 'N/A')}
        Normally gets to class: {row.get('10. When do you normally get to class?', 'N/A')}
        Where they sit in class: {row.get('14. Where do you sit in class?', 'N/A')}
        Drink choice at Erika: {row.get('15. What is your drink of choice at Erika (ERREKA)?', 'N/A')}
        Coffee or Tea Team: {row.get('8. What team are you?', 'N/A')}
        
        ### PERSONALIZED INPUT SPACE (PUBLIC) ###
        [HERE TYPE YOUR PUBLIC INPUT / IMPRESSION OF {name}]: 
        
        """
        
        # We can try to look up their extra gossip by full name, or by first name
        extra_gossip = GOSSIP_DATA.get(name, "")
        if not extra_gossip:
            # try finding by first name loosely
            first_name = name.split(" ")[0].strip()
            for key in GOSSIP_DATA:
                if first_name.lower() in key.lower():
                    extra_gossip = GOSSIP_DATA[key]
                    break
        
        # --- 2) The Spicy Info Chunk ---
        # Putting more personal, secret, or quirky facts here
        spicy_data = f"""
        Name: {name}
        Marital Status: {row.get('3. Marital status', 'N/A')}
        Siblings: {row.get('1. Do you have siblings', 'N/A')}
        Pets: {row.get('2. Do you have any pets?', 'N/A')}
        Plays Instruments: {row.get('4. Do you play any instruments', 'N/A')}
        Productivity Style: {row.get('5. When are you more productive?', 'N/A')}
        Tattoos: {row.get('6. Do you have any tattoos?', 'N/A')}
        Right-handed: {row.get('7. Are you right-handed?', 'N/A')}
        Likes Spicy Food: {row.get('9. Do you like spicy food?', 'N/A')}
        Uses Glasses in Class: {row.get('12. Do you use glasses in class?', 'N/A')}
        Procrastinates: {row.get('13. Do you procrastinate homework/studying?', 'N/A')}
        
        Extra Juicy Gossip & Inside Jokes: 
        {extra_gossip}
        
        ### PERSONALIZED INPUT SPACE (SPICY) ###
        [HERE TYPE YOUR SPICY INPUT / GOSSIP ABOUT {name}]: 
        
        """
        
        # Add Public Data
        documents.append(public_data.strip())
        metadatas.append({"data_tier": "public", "person": name})
        ids.append(str(uuid.uuid4()))
        
        # Add Spicy Data
        documents.append(spicy_data.strip())
        metadatas.append({"data_tier": "spicy", "person": name})
        ids.append(str(uuid.uuid4()))
        
    print(f"Inserting {len(documents)} chunks to ChromaDB...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print("Done! You can now manually edit checking this script to type your input where the placeholders are before re-running.")

if __name__ == "__main__":
    process_csv_and_insert()
