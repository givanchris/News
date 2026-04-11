#!/bin/bash
cd ~/Desktop/Claude/Projects/News
echo "Deploying your site..."
netlify deploy --prod --dir .
echo ""
echo "Done! Press any key to close."
read -n 1
