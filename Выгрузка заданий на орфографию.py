import requests
from bs4 import BeautifulSoup
import re # Import regex for more robust answer extraction
import json # Import json to save to a file

def scrape_problems_and_answers(page_url, start_problem_num):
    try:
        response = requests.get(page_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL {page_url}: {e}")
        return [], 0

    soup = BeautifulSoup(response.text, 'html.parser')
    problems_data_on_page = []

    problem_containers = soup.find_all('div', class_='prob_view')

    if not problem_containers:
        print(f"No problem containers found on {page_url}. Please check the class name.")
        return [], 0

    current_problem_num = start_problem_num
    # Process all problem containers
    for problem_container in problem_containers:
        problem_text = "N/A"
        answer_text = "N/A"

        # Get the full text content of the problem container
        full_content = problem_container.get_text(separator=' ', strip=True)
        # Clean up unwanted characters from the full content before splitting
        full_content = full_content.replace('\xad', '').replace('\u202f', ' ').strip()

        # Determine the end of the problem text: before 'Ответ:' or 'Пояснение', whichever comes first.
        answer_keyword_index = full_content.find("Ответ:")
        explanation_start_match = re.search(r'Пояснение[\s.:]', full_content)
        explanation_index = explanation_start_match.start() if explanation_start_match else -1

        end_of_problem_text_index = len(full_content) # Default to end of content

        if answer_keyword_index != -1 and explanation_index != -1:
            end_of_problem_text_index = min(answer_keyword_index, explanation_index)
        elif answer_keyword_index != -1:
            end_of_problem_text_index = answer_keyword_index
        elif explanation_index != -1:
            end_of_problem_text_index = explanation_index

        # Extract problem text from the beginning of full_content to the determined end_of_problem_text_index
        # Now, specifically starting from 'Укажите варианты ответов'
        start_problem_text_marker = "Укажите варианты ответов"
        problem_start_index = full_content.find(start_problem_text_marker)

        if problem_start_index != -1:
            problem_text = full_content[problem_start_index:end_of_problem_text_index].strip()
        else:
            # If marker not found, still use previous logic but it might be 'N/A'
            problem_text = full_content[:end_of_problem_text_index].strip()

        if not problem_text: # If problem_text is empty after stripping, mark as N/A
            problem_text = "N/A"

        # Extract answer text based on 'Ответ:' marker, expecting digits, and format as 'Ответ: [digits]'
        # The regex currently captures only digits, effectively ignoring any trailing '.' or '|'
        answer_match = re.search(r'Ответ:\s*(\d+)[.|]?', full_content, re.IGNORECASE)
        if answer_match:
            answer_value = answer_match.group(1).strip()
            answer_text = f"Ответ: {answer_value}"
        else:
            answer_text = "Ответ не найден."

        # Post-process problem_text to add newlines for numbered options
        if problem_text != "N/A":
            # 1. Normalize spaces around option numbers and mark their start
            #    This handles variations like ' 1)' or '1)' or '  1)'
            problem_text = re.sub(r'\s*(\d+\)\s*)', r'###OPTION_START###\1', problem_text)

            # 2. Insert two newlines before the first option (expected to be '1)')
            #    We only replace the first occurrence of '###OPTION_START###1)'
            problem_text = problem_text.replace('###OPTION_START###1)', '\n\n1)', 1)

            # 3. Insert one newline before all other options (using the remaining markers)
            problem_text = problem_text.replace('###OPTION_START###', '\n')

            # 4. Consolidate any sequences of three or more newlines into two newlines
            problem_text = re.sub(r'\n{3,}', '\n\n', problem_text)

            # Ensure no leading/trailing whitespace after all formatting
            problem_text = problem_text.strip()

        # Final cleanup for problem_text and answer_text (in case they weren't cleaned fully or N/A)
        # These replace operations handle non-breaking spaces and soft hyphens.
        problem_text = problem_text.replace('\xad', '').replace('\u202f', ' ').replace('...', '..').strip()
        answer_text = answer_text.replace('\xad', '').replace('\u202f', ' ').strip()

        # Only add to results if we successfully extracted both meaningful problem text AND answer.
        if problem_text != "N/A" and answer_text != "Ответ не найден.":
            problems_data_on_page.append({
                'problem_number': current_problem_num,
                'problem_text': problem_text,
                'answer_explanation': answer_text
            })
            current_problem_num += 1
        else:
            print(f"DEBUG: Skipping problem {current_problem_num} due to extraction issues. Page: {page_url}. Problem Text: '{problem_text}' (Length: {len(problem_text)}). Answer Text: '{answer_text}' (Length: {len(answer_text) if answer_text else 0}).")
            current_problem_num += 1 # Increment even if skipped to maintain correct numbering for subsequent problems

    return problems_data_on_page, current_problem_num

ege_tasks_1_data = [] # New list to store scraped data
global_next_problem_num = 1

# Scrape from the first URL (2 pages)
original_base_url = "https://rus-ege.sdamgia.ru/test?category_id=380&filter=all"
print(f"Scraping from: {original_base_url}")
for page_num in range(1, 3): # Pages 1 and 2
    page_url = f"{original_base_url}&page={page_num}" if page_num > 1 else original_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# Scrape from the second URL (9 pages)
new_base_url = "https://rus-ege.sdamgia.ru/test?category_id=358&filter=all"
print(f"\nScraping from: {new_base_url}")
for page_num in range(1, 10): # Pages 1 to 9
    page_url = f"{new_base_url}&page={page_num}" if page_num > 1 else new_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# Scrape from the third URL (17 pages)
third_base_url = "https://rus-ege.sdamgia.ru/test?category_id=259&filter=all"
print(f"\nScraping from: {third_base_url}")
for page_num in range(1, 18): # Pages 1 to 17
    page_url = f"{third_base_url}&page={page_num}" if page_num > 1 else third_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 1: 4 pages from category_id=381
fourth_base_url = "https://rus-ege.sdamgia.ru/test?category_id=381&filter=all"
print(f"\nScraping from: {fourth_base_url}")
for page_num in range(1, 5): # Pages 1 to 4
    page_url = f"{fourth_base_url}&page={page_num}" if page_num > 1 else fourth_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 2: 5 pages from category_id=344
fifth_base_url = "https://rus-ege.sdamgia.ru/test?category_id=344&filter=all"
print(f"\nScraping from: {fifth_base_url}")
for page_num in range(1, 6): # Pages 1 to 5
    page_url = f"{fifth_base_url}&page={page_num}" if page_num > 1 else fifth_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 3: 19 pages from category_id=348
sixth_base_url = "https://rus-ege.sdamgia.ru/test?category_id=348&filter=all"
print(f"\nScraping from: {sixth_base_url}")
for page_num in range(1, 20): # Pages 1 to 19
    page_url = f"{sixth_base_url}&page={page_num}" if page_num > 1 else sixth_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 4: 4 pages from category_id=382
seventh_base_url = "https://rus-ege.sdamgia.ru/test?category_id=382&filter=all"
print(f"\nScraping from: {seventh_base_url}")
for page_num in range(1, 5): # Pages 1 to 4
    page_url = f"{seventh_base_url}&page={page_num}" if page_num > 1 else seventh_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 5: 4 pages from category_id=343
eighth_base_url = "https://rus-ege.sdamgia.ru/test?category_id=343&filter=all"
print(f"\nScraping from: {eighth_base_url}")
for page_num in range(1, 5): # Pages 1 to 4
    page_url = f"{eighth_base_url}&page={page_num}" if page_num > 1 else eighth_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 6: 20 pages from category_id=351
ninth_base_url = "https://rus-ege.sdamgia.ru/test?category_id=351&filter=all"
print(f"\nScraping from: {ninth_base_url}")
for page_num in range(1, 21): # Pages 1 to 20
    page_url = f"{ninth_base_url}&page={page_num}" if page_num > 1 else ninth_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 7: 3 pages from category_id=383
tenth_base_url = "https://rus-ege.sdamgia.ru/test?category_id=383&filter=all"
print(f"\nScraping from: {tenth_base_url}")
for page_num in range(1, 4): # Pages 1 to 3
    page_url = f"{tenth_base_url}&page={page_num}" if page_num > 1 else tenth_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 8: 5 pages from category_id=346
eleventh_base_url = "https://rus-ege.sdamgia.ru/test?category_id=346&filter=all"
print(f"\nScraping from: {eleventh_base_url}")
for page_num in range(1, 6): # Pages 1 to 5
    page_url = f"{eleventh_base_url}&page={page_num}" if page_num > 1 else eleventh_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# New scraping block 9: 20 pages from category_id=350
twelfth_base_url = "https://rus-ege.sdamgia.ru/test?category_id=350&filter=all"
print(f"\nScraping from: {twelfth_base_url}")
for page_num in range(1, 21): # Pages 1 to 20
    page_url = f"{twelfth_base_url}&page={page_num}" if page_num > 1 else twelfth_base_url
    page_problems, global_next_problem_num = scrape_problems_and_answers(page_url, global_next_problem_num)
    ege_tasks_1_data.extend(page_problems)

# Save the results to ege_tasks_1.json
if ege_tasks_1_data:
    with open("ege_tasks_1.json", "w", encoding="utf-8") as f:
        json.dump(ege_tasks_1_data, f, ensure_ascii=False, indent=4)
    print(f"Successfully scraped {len(ege_tasks_1_data)} problems and saved to ege_tasks_1.json")
else:
    print("No relevant data was scraped. Please inspect the webpage's HTML structure and adjust the selectors or filtering logic.")
