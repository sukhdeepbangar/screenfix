const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function success(msg) {
  console.log(`\x1b[32m✓\x1b[0m ${msg}`);
}

function warn(msg) {
  console.log(`\x1b[33m!\x1b[0m ${msg}`);
}

async function uninstall() {
  console.log('\n\x1b[1mUninstalling ScreenFix\x1b[0m\n');

  const installDir = process.cwd();

  // Remove slash commands
  const commandsDir = path.join(installDir, '.claude', 'commands');
  if (fs.existsSync(commandsDir)) {
    const commands = fs.readdirSync(commandsDir).filter(f => f.startsWith('screenfix-'));
    for (const cmd of commands) {
      fs.unlinkSync(path.join(commandsDir, cmd));
    }
    if (commands.length > 0) {
      success(`Removed ${commands.length} slash commands`);
    }
  }

  // Remove screenfix from .mcp.json
  const mcpPath = path.join(installDir, '.mcp.json');
  if (fs.existsSync(mcpPath)) {
    try {
      const config = JSON.parse(fs.readFileSync(mcpPath, 'utf8'));
      if (config.mcpServers?.screenfix) {
        delete config.mcpServers.screenfix;

        // If no other MCP servers, remove the file
        if (Object.keys(config.mcpServers).length === 0) {
          fs.unlinkSync(mcpPath);
          success('Removed .mcp.json (no other servers configured)');
        } else {
          fs.writeFileSync(mcpPath, JSON.stringify(config, null, 2) + '\n');
          success('Removed screenfix from .mcp.json');
        }
      }
    } catch (e) {
      warn('Could not update .mcp.json: ' + e.message);
    }
  }

  // Uninstall Python package
  try {
    execSync('python3 -m pip uninstall -y screenfix', {
      encoding: 'utf8',
      stdio: 'pipe'
    });
    success('Uninstalled Python package');
  } catch {
    warn('Python package may not have been installed');
  }

  console.log('\n\x1b[32mScreenFix uninstalled.\x1b[0m\n');
  console.log('Note: Screenshots in ./screenfix/ were not deleted.\n');
}

module.exports = uninstall;
