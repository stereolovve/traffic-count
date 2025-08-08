#!/usr/bin/env node

const { exec } = require('child_process');
const os = require('os');

function playSound() {
  const platform = os.platform();
  
  switch (platform) {
    case 'darwin': // macOS
      exec('afplay /System/Library/Sounds/Glass.aiff');
      break;
    case 'win32': // Windows
      exec('powershell -c "(New-Object Media.SoundPlayer \'/Windows/Media/notify.wav\').PlaySync();"');
      break;
    case 'linux': // Linux
      exec('paplay /usr/share/sounds/alsa/Front_Left.wav || aplay /usr/share/sounds/alsa/Front_Left.wav');
      break;
    default:
      console.log('🔔 Claude Code response completed!');
  }
}

playSound();