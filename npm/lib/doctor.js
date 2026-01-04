const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

function check(name, fn) {
  try {
    const result = fn();
    if (result === true) {
      console.log(`\x1b[32m✓\x1b[0m ${name}`);
      return true;
    } else if (result === false) {
      console.log(`\x1b[31m✗\x1b[0m ${name}`);
      return false;
    } else {
      console.log(`\x1b[32m✓\x1b[0m ${name}: ${result}`);
      return true;
    }
  } catch (e) {
    console.log(`\x1b[31m✗\x1b[0m ${name}: ${e.message}`);
    return false;
  }
}

async function doctor() {
  console.log('\n\x1b[1mScreenFix Diagnostics\x1b[0m\n');

  const installDir = process.cwd();
  let allPassed = true;

  // Check macOS
  allPassed &= check('macOS', () => {
    if (process.platform !== 'darwin') {
      throw new Error('ScreenFix only works on macOS');
    }
    return true;
  });

  // Check Python version
  allPassed &= check('Python 3.10+', () => {
    const version = execSync('python3 --version', { encoding: 'utf8' }).trim();
    const match = version.match(/Python (\d+)\.(\d+)/);
    if (!match) throw new Error('Could not determine version');
    const major = parseInt(match[1], 10);
    const minor = parseInt(match[2], 10);
    if (major < 3 || (major === 3 && minor < 10)) {
      throw new Error(`Found ${major}.${minor}, need 3.10+`);
    }
    return `${major}.${minor}`;
  });

  // Check screenfix package installed
  allPassed &= check('screenfix Python package', () => {
    try {
      execSync('python3 -c "import screenfix"', { encoding: 'utf8', stdio: 'pipe' });
      return true;
    } catch {
      throw new Error('Not installed. Run: npx create-screenfix');
    }
  });

  // Check .mcp.json exists
  allPassed &= check('.mcp.json exists', () => {
    const mcpPath = path.join(installDir, '.mcp.json');
    if (!fs.existsSync(mcpPath)) {
      throw new Error('Not found');
    }
    return true;
  });

  // Check .mcp.json has screenfix config
  allPassed &= check('.mcp.json has screenfix config', () => {
    const mcpPath = path.join(installDir, '.mcp.json');
    if (!fs.existsSync(mcpPath)) {
      throw new Error('.mcp.json not found');
    }
    const config = JSON.parse(fs.readFileSync(mcpPath, 'utf8'));
    if (!config.mcpServers?.screenfix) {
      throw new Error('screenfix not configured');
    }
    return true;
  });

  // Check slash commands exist
  allPassed &= check('Slash commands installed', () => {
    const commandsDir = path.join(installDir, '.claude', 'commands');
    if (!fs.existsSync(commandsDir)) {
      throw new Error('.claude/commands not found');
    }
    const commands = fs.readdirSync(commandsDir).filter(f => f.startsWith('screenfix-'));
    if (commands.length === 0) {
      throw new Error('No screenfix commands found');
    }
    return `${commands.length} commands`;
  });

  // Check daemon state
  allPassed &= check('Daemon status', () => {
    const statePath = path.join(os.homedir(), '.config', 'screenfix', 'state.json');
    if (!fs.existsSync(statePath)) {
      return 'Not running';
    }
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    if (state.listening) {
      return `Running (PID: ${state.pid})`;
    }
    return 'Not running';
  });

  console.log('');

  if (allPassed) {
    console.log('\x1b[32mAll checks passed!\x1b[0m\n');
  } else {
    console.log('\x1b[33mSome checks failed. Run "npx create-screenfix" to fix.\x1b[0m\n');
    process.exit(1);
  }
}

module.exports = doctor;
