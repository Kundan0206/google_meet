# Use Windows Server Core LTSC 2022 as base image
FROM mcr.microsoft.com/powershell:ltsc2022

# Metadata
LABEL maintainer="kundanbhure7@gmail.com"

# Set PowerShell as the default shell
SHELL ["powershell", "-Command"]

# Install Chocolatey
RUN Set-ExecutionPolicy Bypass -Scope Process -Force ; \
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072 ; \
    iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Install Python 3.11.0, Google Chrome, Git
RUN choco install -y python --version=3.11.0 ; \
    choco install -y googlechrome ; \
    choco install -y git

# Add Python to PATH explicitly
ENV PATH="C:\\Python311;C:\\Python311\\Scripts;${PATH}"

# Install FFmpeg
RUN choco install -y ffmpeg

# Install Python packages
RUN pip install --upgrade pip ; \
    pip install selenium undetected-chromedriver openai-whisper

# Create working directory
WORKDIR C:/app

# Copy your script into the container
COPY google_meet_bot.py .

# Set environment variables
ENV MEET_URL="https://meet.google.com/guc-pxfz-jpe" \
    RECORDING_DURATION="3600" \
    OUTPUT_FILE="meet_recording.mp4" \
    AUDIO_DEVICE="Microphone Array (Intel® Smart Sound Technology for Digital Microphones)" \
    TRANSCRIBE="True"

# Run the script
CMD ["python", "google_meet_bot.py"]
