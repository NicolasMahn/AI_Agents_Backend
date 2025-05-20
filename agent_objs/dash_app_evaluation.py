import os
import time

from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from llm_functions.llm_api_wrapper import get_image_description

DASH_LINK = os.getenv("DASH_LINK", "http://localhost")

TIMEOUT = 10000

def evaluate_dash_app(port=8050, code_dir="screenshots"):
    try:
        html_body, screenshot_path = get_dash_code_and_screenshot(port=port, screenshot_path=f"{code_dir}/screenshot.png")
        if not screenshot_path: # In case of error screenshot_path is None
            return html_body # and html_body is the error message
    except Exception as e:
        return f"An error occurred while taking the screenshot or extracting the html: {e}"

    # Get image evaluation of the screenshot
    task = f"""
Analyze the provided screenshot of a Dash web application. Use the accompanying HTML content to aid your analysis.

**1. Visual Description:**
   - Describe the overall layout and visual elements present in the screenshot (e.g., titles, graphs, tables, input controls, text areas).
   - What does a user visually encounter when first looking at this application interface?

**2. Application Purpose and Functionality:**
   - Based on the visual content and layout, what do you infer is the primary purpose of this application?
   - What kind of data or process does it seem to manage or visualize?
   - What key tasks do you believe a user can accomplish with this application?

**3. Interactive Elements Analysis:**
   - Identify all interactive elements visible in the screenshot (buttons, dropdowns, sliders, input fields, checkboxes, radio buttons, clickable areas in graphs, etc.).
   - **Important Exclusion:** Do **not** include standard Dash debug UI elements (like the debug menu button, callback graph button, etc., often found in a corner) in the XML list below. Focus only on the application's specific controls designed for the end-user.
   - For each interactive element, describe its appearance, its likely function, and the expected outcome of interacting with it.
   - Present this analysis in the following XML format:
     ```xml
     <interactions>
        <element type="button" name="Submit Query" description="Appears to submit the selected options to refresh data or trigger a calculation."/>
        <element type="dropdown" name="Select Region" description="Likely allows the user to filter data based on a geographic region. Selecting an option would update the displayed graphs/tables."/>
        <element type="slider" name="Year Range" description="Probably used to select a range of years, filtering the data shown in the application."/>
        <element type="input_field" name="Search Term" description="Allows the user to enter text, possibly for searching or filtering data."/>
        <element type="checkbox" name="Show Advanced Options" description="Toggles the visibility of additional settings or data views."/>
        <element type="graph_interaction" name="Main Chart" description="Clicking on data points or legends might highlight data, filter other elements, or display tooltips with more information."/>
        <element type="other" name="Specific UI Component" description="Describe any other interactive component and its expected behavior."/>
     </interactions>
     ```
   - Use the provided HTML to help identify element types, labels, or default values if they are not clear from the image alone.
   ```html\n{html_body}\n```

**4. Debug Information:**
   - Examine the bottom of the screenshot for a debug footer or console output.
   - If any error messages, warnings, or stack traces are visible, quote them exactly in your description. If none are visible, state that.

**5. Overall Assessment:**
   - Briefly summarize the apparent state of the application. Does it look functional? Are there any obvious visual glitches, layout problems, or inconsistencies (aside from potential debug errors)?
"""

    return get_image_description(screenshot_path, task)


def is_dash_server_responding(port, retries=10, delay=1):
    """Checks if the server responds with a successful HTTP status code."""
    url = f"{DASH_LINK}:{port}/"
    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code >= 200 and response.status_code < 300:
                return True

        except Exception as e:
            pass

        if i < retries - 1:
            time.sleep(delay)
    print(f"Failed to connect to {url} after {retries} attempts.")
    return False



def get_dash_code_and_screenshot(port=8050, screenshot_path="screenshot.png", loading_element_class="_dash-loading"):
    """
    Evaluates the fully rendered HTML output of a Dash application
    running in a Docker container using a headless browser (Playwright).

    Args:
        port (int): The port number where the Dash app is running.
        screenshot_path (str): The file path to save the screenshot.
        loading_element_class (str, optional): The class of a loading element to wait for its disappearance.
                                            Defaults to "_dash-loading".

    Returns:
        str: The fully rendered HTML content of the Dash app,
             or None if an error occurs or timeout is reached.

    Requires:
        - playwright library installed (`pip install playwright`)
        - Browser binaries installed via `playwright install` within the
          execution environment (e.g., the Docker container).
    """
    # Playwright expects timeout in milliseconds
    playwright_timeout = TIMEOUT
    url = f"{DASH_LINK}:{port}"  # Use localhost as Playwright runs on the host accessing the container's exposed port


    try:
        if is_dash_server_responding(port):

            with sync_playwright() as p:
                # Launch Chromium browser. You can also use p.firefox.launch() or p.webkit.launch()
                # Pass necessary arguments for running in Docker/headless environments
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",  # Necessary for running as root in Docker
                        "--disable-dev-shm-usage",  # Overcome limited resource problems
                        "--disable-gpu"  # Sometimes necessary in headless environments
                    ]
                )
                page = browser.new_page()

                try:
                    page.goto(url, timeout=playwright_timeout)

                    # Wait for the loading element to disappear
                    if loading_element_class:
                        page.wait_for_function(
                            f"() => !document.querySelector('.{loading_element_class}') || "
                            f"getComputedStyle(document.querySelector('.{loading_element_class}')).display === 'none'",
                            timeout=playwright_timeout
                        )
                        time.sleep(10) # Wait for additional time to ensure the page is fully loaded

                    # Take a screenshot
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"Screenshot saved to {screenshot_path}")

                    html_content_ = page.content()
                    soup = BeautifulSoup(html_content_, 'html.parser')

                    # Remove the footer element if it exists
                    footer = soup.find('footer')
                    if footer:
                        footer.decompose()

                    body_content = soup.body.prettify() if soup.body else None
                    return body_content, screenshot_path

                except PlaywrightTimeoutError:
                    print(
                        f"Playwright Timeout error ({TIMEOUT}s) or element was not found at {url}.")
                    return "Timeout error: Element not found or navigation failed.", None
                finally:
                    # Ensure the browser is closed
                    browser.close()

    except Exception as e:
        # Catch any other unexpected errors (e.g., Playwright installation issues)
        print(f"An unexpected error occurred: {e}")
        return f"An unexpected error occurred. {e}", None


if __name__ == "__main__":
    # Example usage
    # port = 58935 #
    port = 8050
    html_content = evaluate_dash_app(port)
    if html_content:
        print("Rendered HTML content:")
        print(html_content)
    else:
        print("Failed to retrieve rendered HTML content.")