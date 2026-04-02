from data_processing import get_linkedin_profile_data

def run_test():
    print("Testing LinkedIn Scraper API on one profile...")
    test_url = "https://www.linkedin.com/in/jadzoghaib/" # Using your profile as a test!
    
    result = get_linkedin_profile_data(test_url)
    
    print("\n" + "="*40)
    print("SCRAPED DATA RESULT:")
    print("="*40)
    print(result)
    print("="*40 + "\n")
    print("If you see your experience and education above, the API is working perfectly!")
    print("You can now run 'python data_processing.py' to process everyone.")

if __name__ == "__main__":
    run_test()
