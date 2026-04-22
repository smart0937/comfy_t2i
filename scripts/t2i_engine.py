import json
import requests
import time
import os
import sys
import random
import argparse

# Configuration
COMPYUI_URL = "http://172.16.1.3:8188"
DEFAULT_WORKFLOW = os.path.expanduser("~/.hermes/skills/mlops/comfy_t2i/references/01-Flux2-Klein-T2I.json")
DELIVERY_DIR = os.path.expanduser("~/.hermes/hermes-agent/output")
T2I_PROMPT_NODE_ID = "107"
NOISE_SEED_NODE_ID = "93"

def run_automation():
    parser = argparse.ArgumentParser(description="ComfyUI T2I Automation")
    parser.add_argument("workflow", nargs="?", default=DEFAULT_WORKFLOW, help="Path to workflow JSON")
    parser.add_argument("prompt", nargs="?", default="A high-quality, realistic photograph.", help="Prompt text")
    parser.add_argument("--user_id", type=str, default=None, help="Telegram User ID for filename isolation")
    
    args = parser.parse_args()
    
    workflow_path = args.workflow
    edit_prompt_text = args.prompt
    user_id = args.user_id

    # Generate unique filename
    timestamp_ms = int(time.time() * 1000)
    process_id = os.getpid()
    
    if user_id:
        unique_id = f"{user_id}_{timestamp_ms}_{process_id}"
    else:
        unique_id = f"{timestamp_ms}_{process_id}"
        
    transient_file = os.path.join(DELIVERY_DIR, f"t2i_transient_{unique_id}.png")

    try:
        os.makedirs(DELIVERY_DIR, exist_ok=True)
        if not os.path.exists(workflow_path):
            print(f"Error: Workflow not found at {workflow_path}")
            return

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        if T2I_PROMPT_NODE_ID in workflow:
            node_data = workflow[T2I_PROMPT_NODE_ID]
            for key in ["prompt", "text"]:
                if key in node_data.get("inputs", {}):
                    node_data["inputs"][key] = edit_prompt_text
                    print(f"Injected prompt into Node {T2I_PROMPT_NODE_ID} (CR Prompt Text)")
                    break
        else:
            print(f"Error: Node {T2I_PROMPT_NODE_ID} not found in workflow.")
            return

        # Randomize seed to prevent ComfyUI caching
        if NOISE_SEED_NODE_ID in workflow:
            seed_node = workflow[NOISE_SEED_NODE_ID]
            if "inputs" in seed_node and "noise_seed" in seed_node["inputs"]:
                new_seed = random.randint(0, 18446744073709551615)
                seed_node["inputs"]["noise_seed"] = new_seed
                print(f"Randomized seed in Node {NOISE_SEED_NODE_ID} to {new_seed}")
        else:
            print(f"Warning: Seed node {NOISE_SEED_NODE_ID} not found, cache may occur.")

        print("Sending prompt to ComfyUI...")
        payload = {"prompt": workflow}
        prompt_resp = requests.post(f"{COMPYUI_URL}/prompt", json=payload)
        if prompt_resp.status_code != 200:
            print(f"Prompt delivery failed: {prompt_resp.text}")
            return

        prompt_id = prompt_resp.json()["prompt_id"]
        print(f"Prompt ID: {prompt_id}. Polling for completion...")

        start_time = time.time()
        timeout = 600
        output_filename = None

        while time.time() - start_time < timeout:
            history_resp = requests.get(f"{COMPYUI_URL}/history/{prompt_id}")
            history = history_resp.json()
            if prompt_id in history:
                print("Generation complete!")
                outputs = history[prompt_id]["outputs"]
                for node_id, data in outputs.items():
                    if "images" in data:
                        output_filename = data["images"][0]["filename"]
                        img_sub = data["images"][0].get("subfolder", "")
                        img_type = data["images"][0].get("type", "output")

                        download_url = f"{COMPYUI_URL}/view?filename={output_filename}&subfolder={img_sub}&type={img_type}"
                        print(f"Downloading: {download_url}")
                        img_resp = requests.get(download_url, stream=True)
                        if img_resp.status_code == 200:
                            with open(transient_file, 'wb') as f:
                                f.write(img_resp.content)
                            print(f"MEDIA:{transient_file}")
                            print(f"SIGNAL:DELIVERY_COMPLETE:{transient_file}")
                        else:
                            print(f"Download failed: {img_resp.status_code}")
                        break
                break
            time.sleep(10)
        else:
            print("Error: Timeout.")

    except Exception as e:
        print(f"Automation Error: {e}")

if __name__ == "__main__":
    run_automation()
