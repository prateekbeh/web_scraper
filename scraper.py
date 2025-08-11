from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import random
import time
import csv
import json
import os
from datetime import datetime

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

def get_company_links():
    company_links = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1366, 'height': 768}
        )
        page = context.new_page()
        
        try:
            page.goto('https://clutch.co/developers/artificial-intelligence', timeout=60000)
            page.wait_for_timeout(5000)
            
            try:
                cookie_btn = page.query_selector('button:has-text("Accept"), button:has-text("I Accept")')
                if cookie_btn:
                    cookie_btn.click()
                    page.wait_for_timeout(2000)
            except:
                pass
            
            for scroll_round in range(10):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                
                try:
                    load_more_selectors = [
                        'button:has-text("Load more")',
                        'button:has-text("Show more")',
                        'button:has-text("More companies")'
                    ]
                    
                    for selector in load_more_selectors:
                        load_more = page.query_selector(selector)
                        if load_more and load_more.is_visible():
                            load_more.click()
                            page.wait_for_timeout(3000)
                            break
                except:
                    pass
            
            links = page.query_selector_all('a[href*="/profile/"]')
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/profile/' in href and 'clutch.co' in href:
                        if '/package' not in href and '#' not in href:
                            clean_url = href.split('?')[0]
                            if clean_url not in company_links:
                                company_links.append(clean_url)
                except:
                    continue
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
    
    return company_links

def scrape_single_company(company_url, company_number, total_companies):
    print(f"\nCompany {company_number}/{total_companies}: {company_url}")
    time.sleep(random.randint(2, 5))
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(company_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        company_data = {
            'company_rank': company_number,
            'company_name': '',
            'website': '',
            'location': '',
            'city': '',
            'state': '',
            'country': '',
            'description': '',
            'company_size': '',
            'founded_year': '',
            'services': [],
            'industries': [],
            'technologies': [],
            'min_project_size': '',
            'hourly_rate_min': '',
            'hourly_rate_max': '',
            'rating': '',
            'review_count': '',
            'phone': '',
            'email': '',
            'recent_reviews': [],
            'clutch_profile_url': company_url,
            'scraped_at': datetime.now().isoformat()
        }
        
        import re
        
        # Meta tags extraction
        og_title = soup.find('meta', property='og:title')
        if og_title:
            company_data['company_name'] = og_title.get('content', '').strip()
        else:
            name_elem = soup.find('h1')
            if name_elem:
                company_data['company_name'] = name_elem.get_text(strip=True)
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            company_data['description'] = og_desc.get('content', '').strip()
        else:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                company_data['description'] = meta_desc.get('content', '').strip()
        
        locality_meta = soup.find('meta', property='business:contact_data:locality')
        country_meta = soup.find('meta', property='business:contact_data:country_name')
        
        if locality_meta:
            company_data['city'] = locality_meta.get('content', '').strip()
        if country_meta:
            company_data['country'] = country_meta.get('content', '').strip()
        
        location_parts = []
        if company_data['city']:
            location_parts.append(company_data['city'])
        if company_data['country']:
            location_parts.append(company_data['country'])
        if location_parts:
            company_data['location'] = ', '.join(location_parts)
        
        body_text = soup.get_text()
        
        # Website
        visit_website = soup.find('a', string=re.compile(r'Visit\s+Website', re.I))
        if visit_website and visit_website.get('href'):
            company_data['website'] = visit_website['href']
        else:
            website_links = soup.find_all('a', href=re.compile(r'^https?://(?!clutch\.co|www\.clutch\.co)'))
            for link in website_links:
                href = link.get('href', '')
                if not any(domain in href for domain in ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 'youtube.com']):
                    company_data['website'] = href
                    break
        
        if not company_data['website']:
            provider_website_match = re.search(r'"provider_website":"([^"]+)"', str(soup))
            if provider_website_match:
                website = provider_website_match.group(1)
                if not website.startswith('http'):
                    website = 'https://' + website
                company_data['website'] = website
        
        # State
        if company_data['country'] == 'United States' and company_data['city']:
            state_pattern = r'{},\s*([A-Z]{{2}})'.format(re.escape(company_data['city']))
            state_match = re.search(state_pattern, body_text)
            if state_match:
                company_data['state'] = state_match.group(1)
        
        # Rating
        rating_patterns = [r'(\d\.\d)\s*out\s*of\s*5', r'(\d\.\d)\s*stars?', r'rating[:\s]+(\d\.\d)', r'(\d\.\d)/5']
        for pattern in rating_patterns:
            rating_match = re.search(pattern, body_text, re.I)
            if rating_match:
                company_data['rating'] = rating_match.group(1)
                break
        
        # Review count
        review_patterns = [r'(\d+)\s*(?:verified\s+)?reviews?', r'Based\s+on\s+(\d+)\s+reviews?', r'(\d+)\s+client\s+reviews?']
        for pattern in review_patterns:
            review_match = re.search(pattern, body_text, re.I)
            if review_match:
                company_data['review_count'] = review_match.group(1)
                break
        
        # Email
        email_pattern = r'([a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,})'
        email_matches = re.findall(email_pattern, body_text)
        for email in email_matches:
            if not any(exclude in email.lower() for exclude in ['example.com', 'sentry.io', 'segment.com']):
                company_data['email'] = email
                break
        
        # Services
        service_keywords = ['AI Development', 'Machine Learning', 'Custom Software Development', 
                          'Mobile App Development', 'Web Development', 'Cloud Consulting', 
                          'Data Engineering', 'DevOps', 'UI/UX Design']
        for keyword in service_keywords:
            if keyword in body_text:
                company_data['services'].append(keyword)
        
        # Industries
        industry_keywords = ['Healthcare', 'Finance', 'Retail', 'Manufacturing', 'Education', 
                           'Technology', 'Automotive', 'Real Estate', 'E-commerce', 'Fintech']
        for keyword in industry_keywords:
            if keyword in body_text:
                company_data['industries'].append(keyword)
        
        # Technologies
        tech_keywords = ['Python', 'JavaScript', 'React', 'Node.js', 'AWS', 'Azure', 'Docker', 'Kubernetes', 
                        'TensorFlow', 'PyTorch', 'Java', 'PHP', 'Angular', 'Vue.js', 'MongoDB', 'PostgreSQL',
                        '.NET', 'C#', 'TypeScript', 'GraphQL', 'Redis', 'Elasticsearch']
        for tech in tech_keywords:
            if re.search(r'\b' + re.escape(tech) + r'\b', body_text, re.I):
                company_data['technologies'].append(tech)
        
        # Company size
        size_patterns = [r'(\d+)\s*-\s*(\d+)\s*employees?', r'(\d+\+?)\s*employees?']
        for pattern in size_patterns:
            size_match = re.search(pattern, body_text, re.I)
            if size_match:
                company_data['company_size'] = size_match.group(0)
                break
        
        # Founded year
        year_patterns = [r'Founded[:\s]+(\d{4})', r'Established[:\s]+(\d{4})', r'Since[:\s]+(\d{4})', r'Founded\s+in\s+(\d{4})']
        for pattern in year_patterns:
            year_match = re.search(pattern, body_text, re.I)
            if year_match:
                company_data['founded_year'] = year_match.group(1)
                break
        
        # Min project size
        project_match = re.search(r'Min(?:imum)?\s+project\s+size[:\s]*\$?([\d,]+)', body_text, re.I)
        if project_match:
            company_data['min_project_size'] = project_match.group(1).replace(',', '')
        
        # Hourly rate
        rate_match = re.search(r'\$?([\d,]+)\s*-\s*\$?([\d,]+)\s*/\s*hr', body_text, re.I)
        if rate_match:
            company_data['hourly_rate_min'] = rate_match.group(1).replace(',', '')
            company_data['hourly_rate_max'] = rate_match.group(2).replace(',', '')
        
        # Phone
        phone_match = re.search(r'\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', body_text)
        if phone_match:
            company_data['phone'] = phone_match.group(0)
        
        # Reviews
        review_elements = soup.find_all(['div', 'p', 'blockquote'], class_=re.compile('review|testimonial|feedback', re.I))
        for elem in review_elements[:3]:
            review_text = elem.get_text(strip=True)
            if 50 < len(review_text) < 500:
                company_data['recent_reviews'].append(review_text)
        
        return company_data
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def sanitize_filename(name):
    """Remove/replace characters that are invalid in filenames"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()

def save_individual_company(company_data, output_dir='clutch_companies'):
    """Save individual company data to its own CSV file"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    rank = company_data.get('company_rank', 0)
    name = sanitize_filename(company_data.get('company_name', 'unknown'))
    filename = f"company_{rank:03d}_{name}.csv"
    filepath = os.path.join(output_dir, filename)
    
    fieldnames = [
        'company_rank', 'company_name', 'website', 'location', 'city', 'state', 'country',
        'company_size', 'founded_year', 'description', 'services', 'industries',
        'technologies', 'min_project_size', 'hourly_rate_min', 'hourly_rate_max',
        'rating', 'review_count', 'phone', 'email', 'recent_reviews',
        'clutch_profile_url', 'scraped_at'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        row = {}
        for field in fieldnames:
            if field in company_data:
                value = company_data[field]
                if isinstance(value, list):
                    row[field] = ' | '.join(value) if field == 'recent_reviews' else '; '.join(value)
                else:
                    row[field] = value
            else:
                row[field] = ''
        writer.writerow(row)
    
    return filepath

def save_master_file(all_data):
    """Save all company data to master CSV file"""
    if not all_data:
        return
    
    master_filename = 'clutch_ai_companies_complete.csv'
    fieldnames = [
        'company_rank', 'company_name', 'website', 'location', 'city', 'state', 'country',
        'company_size', 'founded_year', 'description', 'services', 'industries',
        'technologies', 'min_project_size', 'hourly_rate_min', 'hourly_rate_max',
        'rating', 'review_count', 'phone', 'email', 'recent_reviews',
        'clutch_profile_url', 'scraped_at'
    ]
    
    with open(master_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for company in all_data:
            row = {}
            for field in fieldnames:
                if field in company:
                    value = company[field]
                    if isinstance(value, list):
                        row[field] = ' | '.join(value) if field == 'recent_reviews' else '; '.join(value)
                    else:
                        row[field] = value
                else:
                    row[field] = ''
            writer.writerow(row)
    
    # Also save as JSON for flexibility
    json_filename = 'clutch_ai_companies_complete.json'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    return master_filename, json_filename

def create_readme():
    """Create README file with methodology documentation"""

    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("Created README.md documentation")

def main():
    print("Clutch.co AI Companies Scraper")
    print("=" * 50)
    
    # Create README documentation
    create_readme()
    
    # Get all company links
    company_links = get_company_links()
    
    if not company_links:
        print("No company links found!")
        return
    
    total_companies = len(company_links)
    print(f"Found {total_companies} companies to scrape")
    
    # Create output directory
    output_dir = 'clutch_companies'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    all_scraped_data = []
    failed_companies = []
    
    # Scrape each company
    for i, company_url in enumerate(company_links, 1):
        try:
            company_data = scrape_single_company(company_url, i, total_companies)
            
            if company_data:
                all_scraped_data.append(company_data)
                # Save individual company file
                filepath = save_individual_company(company_data, output_dir)
                print(f"Success: {company_data.get('company_name', 'Unknown')} - Saved to {filepath}")
            else:
                failed_companies.append(company_url)
            
            # Delay between companies (except after last one)
            if i < total_companies:
                delay = random.randint(5, 15)
                print(f"Waiting {delay} seconds...")
                time.sleep(delay)
            
        except Exception as e:
            print(f"Fatal error: {e}")
            failed_companies.append(company_url)
    
    # Save master file
    if all_scraped_data:
        master_csv, master_json = save_master_file(all_scraped_data)
        print(f"\nMaster files saved: {master_csv} and {master_json}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("SCRAPING COMPLETE")
    print("=" * 50)
    print(f"Total companies found: {total_companies}")
    print(f"Successfully scraped: {len(all_scraped_data)}")
    print(f"Failed: {len(failed_companies)}")
    print(f"Success rate: {len(all_scraped_data) / total_companies * 100:.1f}%")
    print(f"Individual files saved in: {output_dir}/")
    print(f"Master file: clutch_ai_companies_complete.csv")
    
    if failed_companies:
        print("\nFailed URLs:")
        for url in failed_companies:
            print(f"  {url}")

if __name__ == "__main__":
    main()
