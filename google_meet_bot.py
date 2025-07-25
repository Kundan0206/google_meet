from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import os
import time
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
MEET_URL = "https://meet.google.com/guc-pxfz-jpe"  # Replace with your Google Meet link
EMAIL = "kundanbhure7@gmail.com"                # Replace with your Google email
PASSWORD = "Gajanan@1234"          # Replace with your Google password
RECORDING_DURATION = 3600          # Duration in seconds (e.g., 1 hour)
OUTPUT_FILE = "meet_recording.mp4"  # Output file name
AUDIO_DEVICE = "Microphone Array (Intel® Smart Sound Technology for Digital Microphones)"  # Replace with your microphone name from ffmpeg -list_devices
TRANSCRIBE = True                  # Set to True to transcribe with Whisper

def check_ffmpeg():
    """Verify FFmpeg is accessible."""
    try:
        result = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True, check=True)
        logging.info(f"FFmpeg version: {result.stdout.splitlines()[0]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.error(f"FFmpeg not found at {FFMPEG_PATH}.")
        return False

def test_audio_device():
    """Test if the audio device is accessible."""
    try:
        cmd = f'"{FFMPEG_PATH}" -f dshow -i audio="{AUDIO_DEVICE}" -t 5 C:/app/test_audio.mp3'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        logging.info(f"Audio device test successful: {result.stdout[:500]}...")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Audio device test failed: {e.stderr[:500]}...")
        return False

def list_dshow_devices():
    """List DirectShow devices."""
    try:
        result = subprocess.run([FFMPEG_PATH, "-list_devices", "true", "-f", "dshow", "-i", "dummy"], capture_output=True, text=True)
        logging.info(f"DirectShow devices:\n{result.stderr}")
        return result.stderr
    except Exception as e:
        logging.error(f"Failed to list DirectShow devices: {e}")
        return ""

def init_browser():
    """Initialize undetected Chrome browser."""
    chrome_options = Options()
    # Uncomment for production
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--no-sandbox")
    try:
        driver = uc.Chrome(options=chrome_options, version_main=138)
        logging.info("Browser initialized successfully.")
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize browser: {e}")
        raise

def login_to_google(driver):
    """Log in to Google account."""
    try:
        driver.get("https://accounts.google.com/signin")
        logging.info("Navigated to Google login page.")

        email_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )
        email_field.send_keys(EMAIL)
        logging.info("Entered email.")
        
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "identifierNext"))
            )
            next_button.click()
        except:
            logging.info("Falling back to alternative 'Next' button.")
            driver.find_element(By.XPATH, "//button[span[text()='Next']]").click()
        logging.info("Clicked 'Next' after email.")

        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "Passwd"))
        )
        password_field.send_keys(PASSWORD)
        logging.info("Entered password.")

        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "passwordNext"))
            )
            next_button.click()
        except:
            logging.info("Falling back to alternative password 'Next' button.")
            driver.find_element(By.XPATH, "//button[span[text()='Next']]").click()
        logging.info("Clicked 'Next' after password.")

        time.sleep(5)
        logging.info("Logged in to Google successfully.")
    except Exception as e:
        logging.error(f"Login failed: {e}")
        raise

def join_meet(driver):
    """Join the Google Meet session."""
    try:
        driver.get(MEET_URL)
        logging.info(f"Navigated to Google Meet: {MEET_URL}")

        try:
            join_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Join now' or text()='Ask to join']"))
            )
            button_text = join_button.text
            join_button.click()
            logging.info(f"Clicked '{button_text}' button.")
        except:
            logging.info("Falling back to alternative join button.")
            join_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'join')]")
            button_text = join_button.get_attribute("aria-label")
            join_button.click()
            logging.info(f"Clicked alternative join button: {button_text}")

        logging.info("Waiting for meeting to load...")
        for attempt in range(3):
            try:
                WebDriverWait(driver, 40).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'Leave call')] | //div[contains(@class, 'participant')] | //div[contains(@class, 'video')]"))
                )
                logging.info("Detected meeting UI.")
                break
            except TimeoutException:
                logging.warning(f"Attempt {attempt + 1}/3: Could not find meeting UI.")
                if attempt == 2:
                    logging.error("Failed to detect meeting UI after 3 attempts.")
                    logging.info(f"Page source: {driver.page_source[:1000]}...")
                    raise TimeoutException("Failed to confirm meeting join.")
                time.sleep(5)

        logging.info("Joined Google Meet successfully.")
    except Exception as e:
        logging.error(f"Failed to join meeting: {e}")
        logging.info(f"Page source: {driver.page_source[:1000]}...")
        raise

def is_meeting_active(driver):
    """Check if the meeting is still active."""
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'Leave call')] | //div[contains(@class, 'participant')]"))
        )
        return True
    except TimeoutException:
        logging.info("No meeting UI found; meeting may have ended.")
        return False

def start_recording():
    """Start FFmpeg to record audio and video."""
    if not check_ffmpeg():
        raise RuntimeError(f"FFmpeg not found at {FFMPEG_PATH}.")
    
    list_dshow_devices()
    
    # Test audio device
    if test_audio_device():
        try:
            cmd = f'"{FFMPEG_PATH}" -y -f gdigrab -i desktop -f dshow -i audio="{AUDIO_DEVICE}" -c:v libx264 -preset ultrafast -c:a aac {OUTPUT_FILE}'
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logging.info(f"Started recording with audio to {OUTPUT_FILE}.")
            return process
        except Exception as e:
            logging.error(f"Failed to start recording with audio: {e}")
    else:
        logging.warning("Audio device inaccessible; falling back to video-only.")

    # Fallback to video-only
    try:
        cmd = f'"{FFMPEG_PATH}" -y -f gdigrab -i desktop -c:v libx264 -preset ultrafast {OUTPUT_FILE}'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logging.info(f"Started video-only recording to {OUTPUT_FILE}.")
        return process
    except Exception as e:
        logging.error(f"Failed to start video-only recording: {e}")
        raise

def transcribe_recording():
    """Transcribe the recording using Whisper."""
    if TRANSCRIBE and os.path.exists(OUTPUT_FILE):
        try:
            logging.info("Starting transcription...")
            subprocess.run(["whisper", OUTPUT_FILE, "--model", "tiny", "--output_dir", "transcriptions"], check=True)
            logging.info("Transcription completed.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Transcription failed: {e}")

def main():
    """Main function."""
    driver = None
    recording_process = None
    try:
        logging.warning("All participants must be notified of recording!")
        driver = init_browser()
        login_to_google(driver)
        join_meet(driver)
        recording_process = start_recording()

        logging.info(f"Recording for up to {RECORDING_DURATION} seconds...")
        start_time = time.time()
        while time.time() - start_time < RECORDING_DURATION:
            if not is_meeting_active(driver):
                logging.info("Meeting has ended; stopping recording.")
                break
            time.sleep(10)

        if recording_process:
            recording_process.terminate()
            try:
                stdout, stderr = recording_process.communicate(timeout=5)
                if stdout:
                    logging.info(f"FFmpeg stdout: {stdout[:500]}...")
                if stderr:
                    logging.error(f"FFmpeg stderr: {stderr[:500]}...")
            except subprocess.TimeoutExpired:
                logging.warning("FFmpeg did not terminate cleanly; forcing termination.")
                subprocess.run(["taskkill", "/IM", "ffmpeg.exe", "/F"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        transcribe_recording()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise
    finally:
        if recording_process:
            recording_process.terminate()
            try:
                subprocess.run(["taskkill", "/IM", "ffmpeg.exe", "/F"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                logging.error(f"Failed to terminate FFmpeg: {e}")
        if driver:
            try:
                if is_meeting_active(driver):
                    driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Leave call')]").click()
                    logging.info("Clicked 'Leave call' button.")
                    time.sleep(2)
                driver.quit()
                logging.info("Browser closed.")
            except Exception as e:
                logging.error(f"Failed to close browser: {e}")
                driver.quit()

if __name__ == "__main__":
    main()