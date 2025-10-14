#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Script starting ---"
echo "Hello from the execution environment!"
echo "I am running on host: $(hostname)"
echo "My user is: $(whoami)"
echo "Current date is: $(date)"
echo "--- Script finished successfully ---"