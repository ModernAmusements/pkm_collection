# Pokémon TCG Pocket Full Collection Extractor

Extract your complete card collection from Pokémon TCG Pocket by intercepting network traffic.

## Prerequisites

- Mac (this script is designed for macOS)
- iPhone with Pokémon TCG Pocket installed
- Both devices on the same WiFi network

## Step 1: Install mitmproxy

```bash
brew install mitmproxy
```

## Step 2: Find Your Mac's IP Address

```bash
ipconfig getifaddr en0
```

Note this IP address (e.g., `192.168.1.100`).

## Step 3: Start mitmproxy

Open a terminal and run:

```bash
mitmproxy --listen-port 8080 --save-stream mitm_capture
```

Keep this terminal window open. You'll see a live view of network traffic.

## Step 4: Configure iPhone Proxy

1. On your iPhone, go to **Settings** > **WiFi**
2. Tap the **(i)** icon next to your connected WiFi network
3. Scroll down to **HTTP Proxy** and tap it
4. Select **Manual**
5. Enter:
   - **Server**: Your Mac's IP address (from Step 2)
   - **Port**: `8080`
6. Tap **Save**

## Step 5: Install mitmproxy Certificate on iPhone

1. Open Safari on your iPhone
2. Go to: `http://mitm.it`
3. You should see a page with certificate options
4. Tap the **Apple** icon to download the certificate
5. Go to **Settings** > **General** > **VPN & Device Management**
6. Tap the downloaded profile (mitmproxy)
7. Tap **Install** and enter your passcode
8. Go to **Settings** > **General** > **About** > **Certificate Trust Settings**
9. Enable full trust for the mitmproxy certificate

## Step 6: Capture Your Collection

1. Open Pokémon TCG Pocket on your iPhone
2. Go to your card collection
3. **Slowly scroll through your entire collection** - all cards you want to capture must be loaded
4. The mitmproxy window on your Mac should show network activity
5. Once you've scrolled through everything, press `Ctrl+C` in the mitmproxy terminal to stop capture

## Step 7: Run the Extraction Script

```bash
python3 extract_full_collection.py
```

Press ENTER when prompted. The script will:
- Read captured network data from `./mitm_capture`
- Extract all card information
- Generate two output files

## Output Files

| File | Description |
|------|-------------|
| `cards_full.json` | Raw JSON data of all cards |
| `my_cards_full.csv` | Spreadsheet with card details and counts |

## Cleanup (Optional)

To remove the proxy configuration from your iPhone:
1. Go to **Settings** > **WiFi**
2. Tap the **(i)** icon next to your network
3. Scroll to **HTTP Proxy** > **Manual** > change to **Off**

To remove the certificate:
1. Go to **Settings** > **General** > **VPN & Device Management**
2. Tap the mitmproxy profile and select **Remove Profile**

## Troubleshooting

### No cards found
- Ensure you scrolled through your entire collection while mitmproxy was running
- Check that `./mitm_capture` directory exists and contains files

### Certificate errors
- Make sure you enabled full trust in Certificate Trust Settings (Step 5, item 9)
- Try reinstalling the certificate

### Connection issues
- Verify both devices are on the same WiFi network
- Check your Mac's firewall isn't blocking port 8080
- Confirm you entered the correct IP address and port

### mitm.it not loading
- Make sure mitmproxy is running
- Verify the proxy is configured correctly on iPhone
- Try visiting any HTTPS site first to trigger the certificate prompt


### Database Images
- dont use images with slanted cards