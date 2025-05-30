#!/bin/bash

REPO_ROOT_REL_PATH="../.." # Relative path from waveform-generator/tests to repo root
AUDIO_FILE_HOST_PATH="$REPO_ROOT_REL_PATH/test/Main_Audio_test.wav"
OUTPUT_DIR_HOST_PATH="$REPO_ROOT_REL_PATH/generated_waveforms"
OUTPUT_FILENAME="test_output.png"
OUTPUT_FILE_HOST_PATH="$OUTPUT_DIR_HOST_PATH/$OUTPUT_FILENAME"

# Container paths
AUDIO_FILE_CONTAINER_PATH="/test_data/Main_Audio_test.wav" # As mounted in docker-compose.yml
OUTPUT_DIR_CONTAINER_PATH="/usr/src/app/generated_waveforms" # As mounted in docker-compose.yml
OUTPUT_FILE_CONTAINER_PATH="$OUTPUT_DIR_CONTAINER_PATH/$OUTPUT_FILENAME"

echo "Starting waveform generator test..."

# Ensure the output directory exists on the host
mkdir -p "$OUTPUT_DIR_HOST_PATH"
# Remove previous test output if it exists
rm -f "$OUTPUT_FILE_HOST_PATH"

echo "Running waveform generator Docker container..."
# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null
then
    echo "docker-compose could not be found. Please ensure it's installed and in your PATH."
    exit 1
fi

# Go to repo root to run docker-compose commands
cd "$REPO_ROOT_REL_PATH"

docker-compose run --rm waveform_generator node generate-waveform.js --audioUrl="$AUDIO_FILE_CONTAINER_PATH" --outputImagePath="$OUTPUT_FILE_CONTAINER_PATH"

echo "Checking for output file: $OUTPUT_FILE_HOST_PATH"
if [ -f "$OUTPUT_FILE_HOST_PATH" ]; then
  echo "SUCCESS: Waveform image '$OUTPUT_FILENAME' generated successfully in '$OUTPUT_DIR_HOST_PATH'."
  # Optional: check file size if needed
  # filesize=$(stat -c%s "$OUTPUT_FILE_HOST_PATH")
  # if [ "$filesize" -gt "1000" ]; then # Check if file size is > 1KB (basic check)
  #   echo "File size is $filesize bytes."
  # else
  #   echo "WARNING: Output file size is very small ($filesize bytes). Check content."
  # fi
else
  echo "FAILURE: Waveform image not found at '$OUTPUT_FILE_HOST_PATH'."
  echo "Please check the logs from the waveform_generator service."
  exit 1
fi
cd -" # Return to previous directory
