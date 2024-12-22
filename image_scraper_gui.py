import os
import time
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.ttk import Progressbar
from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image
from io import BytesIO
import requests

# Global stop flag
stop_scraping_flag = False

def download_images(search_term, num_images, output_dir, progress_callback):
    global stop_scraping_flag
    downloaded_count = 0

    if not stop_scraping_flag and downloaded_count < num_images:
        downloaded_count += scrape_yandex(search_term, num_images, output_dir, progress_callback)

    if downloaded_count <= num_images:
        downloaded_count += scrape_google(search_term, (num_images - downloaded_count), output_dir, progress_callback)

    if downloaded_count <= num_images:
        downloaded_count += scrape_bing(search_term, (num_images - downloaded_count), output_dir, progress_callback)

    progress_callback(100)  # Ensure progress bar reaches 100% at the end
    return downloaded_count

def scroll_to_load_more(driver, scroll_pause_time=2):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        if stop_scraping_flag:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def scrape_google(search_term, limit, output_dir, progress_callback):
    global stop_scraping_flag
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    url = f"https://www.google.com/search?q={search_term}&tbm=isch"
    driver.get(url)
    time.sleep(2)

    scroll_to_load_more(driver)

    images = driver.find_elements(By.CSS_SELECTOR, "img")
    count = 0
    for img in images:
        if stop_scraping_flag or count >= limit:
            break
        try:
            src = img.get_attribute("src")
            if src and src.startswith("http"):
                if download_image(src, output_dir, f"{count + 1}.jpg"):
                    count += 1
                    progress_callback((count / limit) * 100)
        except Exception as e:
            print("Error downloading image:", e)
    driver.quit()
    return count

def scrape_bing(search_term, limit, output_dir, progress_callback):
    global stop_scraping_flag
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    url = f"https://www.bing.com/images/search?q={search_term}"
    driver.get(url)
    time.sleep(2)

    scroll_to_load_more(driver)

    images = driver.find_elements(By.CSS_SELECTOR, "img.mimg")
    count = 0
    for img in images:
        if stop_scraping_flag or count >= limit:
            break
        try:
            src = img.get_attribute("src")
            if src and src.startswith("http"):
                if download_image(src, output_dir, f"{count + 1}.jpg"):
                    count += 1
                    progress_callback((count / limit) * 100)
        except Exception as e:
            print("Error downloading image:", e)
    driver.quit()
    return count

def scrape_yandex(search_term, limit, output_dir, progress_callback):
    global stop_scraping_flag
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    url = f"https://yandex.com/images/search?text={search_term}"
    driver.get(url)
    time.sleep(1)

    scroll_to_load_more(driver)

    anchors = driver.find_elements(By.CSS_SELECTOR, "a.Link.ContentImage-Cover")

    count = 0
    for i, a in enumerate(anchors):
        if stop_scraping_flag or count >= limit:
            break
        try:
            href = a.get_attribute("href")
            from urllib.parse import urlparse, parse_qs, unquote
            query_string = urlparse(href).query
            params = parse_qs(query_string)
            encoded_img_url = params.get('img_url', [""])[0]
            decoded_img_url = unquote(encoded_img_url)

            if decoded_img_url.startswith("//"):
                decoded_img_url = "https:" + decoded_img_url

            if decoded_img_url.startswith("http"):
                filename = f"{count+1}.jpg"
                if download_image(decoded_img_url, output_dir, filename):
                    count += 1
                    progress_callback((count / limit) * 100)
        except Exception as e:
            print("Error downloading image:", e)

    driver.quit()
    return count

def download_image(url, output_dir, filename):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        content_length = int(response.headers.get("Content-Length", 0))
        if content_length >= 2048:  # >2 KB
            img = Image.open(BytesIO(response.content))
            img.save(os.path.join(output_dir, filename))
            return True
    return False


def start_scraping():
    global stop_scraping_flag
    stop_scraping_flag = False

    search_term = subject_entry.get()
    try:
        num_images = int(number_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number for the images.")
        return

    if not search_term:
        messagebox.showerror("Error", "Please enter a subject.")
        return

    output_dir = filedialog.askdirectory(title="Select Download Folder")
    if not output_dir:
        return

    status_label.config(text="Scraping images...")
    progress_bar["value"] = 0

    def progress_callback(value):
        progress_bar["value"] = value
        app.update_idletasks()

    def run_scraper():
        try:
            count = download_images(search_term, num_images, output_dir, progress_callback)
            if not stop_scraping_flag:
                messagebox.showinfo("Success", f"{count} images downloaded successfully!")
        except Exception as e:
            if not stop_scraping_flag:
                messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            status_label.config(text="Scraping complete." if not stop_scraping_flag else "Scraping stopped.")

    threading.Thread(target=run_scraper, daemon=True).start()


def stop_scraping():
    global stop_scraping_flag
    stop_scraping_flag = True
    status_label.config(text="Stopping scraping...")


# Create the GUI
app = tk.Tk()
app.title("Multi-Source Image Scraper")
app.geometry("400x350")
app.resizable(False, False)

tk.Label(app, text="Subject Name:").pack(pady=5)
subject_entry = tk.Entry(app, width=30)
subject_entry.pack(pady=5)

tk.Label(app, text="Number of Images:").pack(pady=5)
number_entry = tk.Entry(app, width=10)
number_entry.pack(pady=5)

button_frame = tk.Frame(app)
button_frame.pack(pady=10)

scrape_button = tk.Button(button_frame, text="Start Scraping", command=start_scraping, bg="blue", fg="white")
scrape_button.pack(side="left", padx=5)

stop_button = tk.Button(button_frame, text="Stop Scraping", command=stop_scraping, bg="red", fg="white")
stop_button.pack(side="right", padx=5)

status_label = tk.Label(app, text="")
status_label.pack(pady=5)

progress_bar = Progressbar(app, length=300, mode="determinate")
progress_bar.pack(pady=10)

app.mainloop()
