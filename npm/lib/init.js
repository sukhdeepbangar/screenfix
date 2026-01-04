const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

function log(msg) {
  console.log(msg);
}

function success(msg) {
  console.log(`\x1b[32m✓\x1b[0m ${msg}`);
}

function error(msg) {
  console.error(`\x1b[31m✗\x1b[0m ${msg}`);
}

function checkPrerequisites() {
  // Check macOS
  if (process.platform !== 'darwin') {
    throw new Error('ScreenFix only works on macOS');
  }

  // Check Python 3.10+
  try {
    const pythonVersion = execSync('python3 --version', { encoding: 'utf8' });
    const match = pythonVersion.match(/Python (\d+)\.(\d+)/);
    if (!match) {
      throw new Error('Could not determine Python version');
    }
    const major = parseInt(match[1], 10);
    const minor = parseInt(match[2], 10);
    if (major < 3 || (major === 3 && minor < 10)) {
      throw new Error(`Python 3.10+ is required (found ${major}.${minor})`);
    }
    success(`Python ${major}.${minor} detected`);
  } catch (e) {
    if (e.message.includes('Python 3.10+')) {
      throw e;
    }
    throw new Error('Python 3 is not installed. Please install Python 3.10+');
  }

  // Check pip
  try {
    execSync('python3 -m pip --version', { encoding: 'utf8', stdio: 'pipe' });
    success('pip available');
  } catch {
    throw new Error('pip is not available. Please install pip for Python 3');
  }
}

function installPythonPackage(installDir, options) {
  if (options.skipPython) {
    log('Skipping Python package installation (--skip-python)');
    return;
  }

  log('Installing Python dependencies...');

  // Get the path to bundled Python source
  const pythonSrcDir = path.join(__dirname, '..', 'python');

  if (!fs.existsSync(pythonSrcDir)) {
    throw new Error('Bundled Python package not found. Package may be corrupted.');
  }

  try {
    // Install in user mode from bundled source
    execSync(`python3 -m pip install --user "${pythonSrcDir}"`, {
      encoding: 'utf8',
      stdio: 'inherit'
    });
    success('Python package installed');
  } catch (e) {
    throw new Error('Failed to install Python package: ' + e.message);
  }
}

function copyMcpConfig(installDir) {
  const mcpConfig = {
    mcpServers: {
      screenfix: {
        type: 'stdio',
        command: 'python3',
        args: ['-m', 'screenfix.mcp_server']
      }
    }
  };

  const mcpPath = path.join(installDir, '.mcp.json');

  try {
    if (fs.existsSync(mcpPath)) {
      // Merge with existing .mcp.json
      const existing = JSON.parse(fs.readFileSync(mcpPath, 'utf8'));
      existing.mcpServers = existing.mcpServers || {};
      existing.mcpServers.screenfix = mcpConfig.mcpServers.screenfix;
      fs.writeFileSync(mcpPath, JSON.stringify(existing, null, 2) + '\n');
      success('Updated .mcp.json (merged with existing)');
    } else {
      fs.writeFileSync(mcpPath, JSON.stringify(mcpConfig, null, 2) + '\n');
      success('Created .mcp.json');
    }
  } catch (e) {
    throw new Error('Failed to create .mcp.json: ' + e.message);
  }
}

function copySlashCommands(installDir) {
  const commandsDir = path.join(installDir, '.claude', 'commands');
  const templatesDir = path.join(__dirname, '..', 'templates', 'commands');

  try {
    // Create .claude/commands directory if it doesn't exist
    fs.mkdirSync(commandsDir, { recursive: true });

    // Get all command templates
    const commands = fs.readdirSync(templatesDir).filter(f => f.endsWith('.md'));

    for (const cmd of commands) {
      const src = path.join(templatesDir, cmd);
      const dest = path.join(commandsDir, cmd);
      fs.copyFileSync(src, dest);
    }

    success(`Installed ${commands.length} slash commands`);
  } catch (e) {
    throw new Error('Failed to copy slash commands: ' + e.message);
  }
}

async function init(options) {
  console.log('\n\x1b[1mScreenFix Setup\x1b[0m\n');

  const installDir = process.cwd();

  try {
    // Step 1: Check prerequisites
    log('Checking prerequisites...');
    checkPrerequisites();

    // Step 2: Install Python package
    installPythonPackage(installDir, options);

    // Step 3: Copy MCP config
    copyMcpConfig(installDir);

    // Step 4: Copy slash commands
    copySlashCommands(installDir);

    // Done
    console.log('\n\x1b[32m\x1b[1mScreenFix installed successfully!\x1b[0m\n');
    console.log('Next steps:');
    console.log('  1. Restart Claude Code to load the MCP server');
    console.log('  2. Run /screenfix-start to begin');
    console.log('  3. Use Cmd+Ctrl+Shift+4 to capture screenshots\n');

  } catch (e) {
    error(e.message);
    process.exit(1);
  }
}

module.exports = init;
