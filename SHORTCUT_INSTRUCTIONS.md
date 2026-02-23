# Auto-Capture for Pokémon TCG Pocket

## Easiest Method: Screen Recording

1. On iPhone, go to **Settings > Control Center**
2. Tap **+** next to **Screen Recording** to add it
3. Open Pokémon TCG Pocket
4. Swipe down from top-right to open Control Center
5. Long-press the record button (circle)
6. Select **Microphone: Off**, tap **Start Recording**
7. Let it record while you manually scroll through ALL cards
8. Swipe down and tap red bar to stop

## Then extract screenshots on Mac

1. The recording saves to Photos
2. Connect iPhone to Mac
3. Open Photos app, import the recording
4. Copy the video to: `/Users/modernamusmenet/Desktop/tcgp/screenshots/`
5. Run:

```bash
cd /Users/modernamusmenet/Desktop/tcgp
./extract_frames.sh
```

## Or: Use Shortcut (if you want fully automatic)

Create this Shortcut:

1. Open **Shortcuts** > **+** > **Create Shortcut**
2. Add actions:
   - **Repeat** (set to 500 times)
     - **Wait** 0.3 seconds
     - **Take Screenshot**
     - **Save to Photos**
3. Tap **...** > turn OFF **Ask Before Running**
4. Name it **"Auto Capture"**

Run it:
- Open Pokémon TCG Pocket to first card
- Open Shortcuts app
- Tap Auto Capture
- Walk away
- It captures 500 screenshots automatically



i play tcgp. i need to get all my pokemon into a csv to get an overview over my cards their effects and how they work with eachother. i screenshottet every pokemon in my collection.(screenshots/20260221_225701/screenshot_0001.png). you can find it in the project root. lets think about how we can improve