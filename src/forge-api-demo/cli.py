import argparse
import json
import logging
import os
import sys
import time

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():

    completion_url = "https://forge-api.nousresearch.com/v1/asyncplanner/completions"
    
    # Parse arguments
    parser = argparse.ArgumentParser(
                    prog='forge-api-demo',
                    description='Simple demo of the Forge API by Nous Research. Run with env var FORGE_API_KEY set.',
                    epilog='For more information, see: https://forge-api.nousresearch.com/docs')
    parser.add_argument("-p", "--prompt",
                        help="Your prompt.",
                        type=str,
                        required=True)
    parser.add_argument("-r", "--reasoning-speed", help="The reasoning preset to use: fast/medium/slow. Defaults to medium.",
                        default="medium",
                        type=str,
                        choices=["fast", "medium", "slow"],
                        action="store")
    parser.add_argument("-t", "--track",
                        help="Whether to return detailed information about the reasoning process.",
                        action="store_true")
    args = parser.parse_args()

    # Get the API key from environment variable
    api_key = os.getenv("FORGE_API_KEY")
    if not api_key:
        logger.error("Please set env var FORGE_API_KEY to your personal API key.") 
        sys.exit(1)


    # Send POST request to initiate completion
    headers = {"Authorization": f"Bearer {api_key}"}    
    post_payload = {
          "prompt": args.prompt,
          "reasoning_speed": args.reasoning_speed,
          "track": args.track
    }
    try:
        logger.info(f"Initiating completion with prompt: {args.prompt}")
        post_response = requests.post(completion_url, json=post_payload, headers=headers, timeout=10)
        post_response.raise_for_status()
    except:
        logger.exception("Failed to initiate completion")
        sys.exit(1)

    # Extract task ID from completion response
    try:
        post_response_data = post_response.json()
        if 'task_id' in post_response_data:
            task_id = post_response_data['task_id']
            logger.info(f"Completion initiated. Check on its status any time at {completion_url}/{task_id}")
        else:
            raise ValueError("Error: Task ID not found in response: " + str(post_response_data))
    except:
        logger.exception("Failed to initiate completion")
        sys.exit(1)

    # Poll until target string is found in response
    poll_url = f"{completion_url}/{task_id}"    
    waited_s = 0
    poll_failures = 0
    start_time = time.time()
    while waited_s < 300: # timeout after 5 minutes
        time.sleep(5)
        waited_s = time.time() - start_time        
        try:
            poll_response = requests.get(poll_url, headers=headers, timeout=10)
            poll_response.raise_for_status()
            poll_response_data = poll_response.json()           
            polled_status = poll_response_data['metadata']['status'] if 'metadata' in poll_response_data else "unknown"
            if polled_status == 'succeeded':
                logger.info(f"Done! Completion took {waited_s:.2f}s. Full results will be available for 24h at {poll_url}")
                print(json.dumps(poll_response_data, indent=2))
                return
            elif polled_status == 'failed':
                logger.error("Failed! Completion failed.")
                print(json.dumps(poll_response_data, indent=2))
                sys.exit(1)
            elif polled_status == 'cancelled':
                logger.warning("Completion cancelled.")
                print(json.dumps(poll_response_data, indent=2))
                sys.exit(1)

            logger.info(f"Waiting for completion. This can take a while! Current status: {polled_status}  (waited: {waited_s:.2f}s)...") 
            poll_failures = 0
        except Exception as e:
            logger.warning(f"Polling request failed: {e}")
            poll_failures += 1
            if poll_failures > 5:
                logger.exception(f"Failed to poll for completion after {poll_failures} attempts. Giving up.\n")
                sys.exit(1)

if __name__ == "__main__":
    main()
