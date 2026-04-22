import json
import requests
import time
import os
import sys
import random

# Configuration
COMPYUI_URL = "http://172.16.1.3:8188"
DEFAULT_WORKFLOW = os.path.expanduser("~/.hermes/skills/mlops/comfy_t2i/references/01-Flux2-Klein-T2I.json")
WORKFLOW_PATH = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WORKFLOW
EDIT_PROMPT_TEXT = sys.argv[2] if len(sys.argv) > 2 else "A high-quality, realistic photograph."

DELIVERY_DIR = os.path.expanduser("~/.hermes/hermes-agent/output")
TRANSIENT_FILE = os.path.join(DELIVERY_DIR, "t2i_transient_output.png")
T2I_PROMPT_NODE_ID = "107"
NOISE_SEED_NODE_ID = "93"

def run_automation():
    try:
        os.makedirs(DELIVERY_DIR, exist_ok=True)
        if not os.path.exists(WORKFLOW_PATH):
            print(f"Error: Workflow not found at {WORKFLOW_PATH}")
            return

        with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        if T2I_PROMPT_NODE_ID in workflow:
            node_data = workflow[T2I_PROMPT_NODE_ID]
            for key in ["prompt", "text"]:
                if key in node_data.get("inputs", {}):
                    node_data["inputs"][key] = EDIT_PROMPT_TEXT
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
                            with open(TRANSIENT_FILE, 'wb') as f:
                                f.write(img_resp.content)
                            print(f"MEDIA:{TRANSIENT_FILE}")
                            print(f"SIGNAL:DELIVERY_COMPLETE:{TRANSIENT_FILE}")
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
