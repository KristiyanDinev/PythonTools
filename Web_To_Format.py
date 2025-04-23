import asyncio
from playwright.async_api import async_playwright

async def url_to_pdf(url, output_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        # Wait until network is idle to ensure all content is loaded
        await page.wait_for_load_state('networkidle')

        # Get the full dimensions of the page
        dimensions = await page.evaluate('''() => {
            return {
                width: document.documentElement.scrollWidth,
                height: document.documentElement.scrollHeight
            }
        }''')

        # Convert pixels to inches (1 inch = 96 pixels)
        width_in = (dimensions['width'] / 96) + 2.5
        height_in = dimensions['height'] / 96

        # Generate the PDF with custom width and height
        await page.pdf(
            path=output_path,
            print_background=True,
            width=f"{width_in}in",
            height=f"{height_in}in",
            scale=1,
        )

        await browser.close()

async def url_to_png(url, output_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)

        # Wait for the page to load completely
        await page.wait_for_load_state('networkidle')

        # Take a full-page screenshot
        await page.screenshot(path=output_path, full_page=True)

        await browser.close()

# Example usage
url = input("Full url: ")

temp = input("Convert to PDF (Default yes) / the other option is .png screenshot of the website? ").replace(" ", "").lower()
isPDF = len(temp) == 0 or temp == "yes" or temp == "y"

output_path = input("Full path for output file: ")

if isPDF:
    asyncio.run(url_to_pdf(url, output_path))

else:
    asyncio.run(url_to_png(url, output_path))

# python -m pip install playwright
# python -m playwright install

# python -m playwright uninstall
# python -m pip uninstall playwright
