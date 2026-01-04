const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function success(msg) {
  console.log(`\x1b[32m✓\x1b[0m ${msg}`);
}

function log(msg) {
  console.log(msg);
}

async function update() {
  console.log('\n\x1b[1mUpdating ScreenFix\x1b[0m\n');

  const installDir = process.cwd();

  // Re-install Python package from bundled source
  log('Updating Python package...');
  const pythonSrcDir = path.join(__dirname, '..', 'python');

  if (!fs.existsSync(pythonSrcDir)) {
    console.error('\x1b[31m✗\x1b[0m Bundled Python package not found');
    process.exit(1);
  }

  try {
    execSync(`python3 -m pip install --user --upgrade "${pythonSrcDir}"`, {
      encoding: 'utf8',
      stdio: 'inherit'
    });
    success('Python package updated');
  } catch (e) {
    console.error('\x1b[31m✗\x1b[0m Failed to update Python package');
    process.exit(1);
  }

  // Re-copy slash commands (in case of updates)
  log('Updating slash commands...');
  const commandsDir = path.join(installDir, '.claude', 'commands');
  const templatesDir = path.join(__dirname, '..', 'templates', 'commands');

  try {
    fs.mkdirSync(commandsDir, { recursive: true });

    const commands = fs.readdirSync(templatesDir).filter(f => f.endsWith('.md'));
    for (const cmd of commands) {
      const src = path.join(templatesDir, cmd);
      const dest = path.join(commandsDir, cmd);
      fs.copyFileSync(src, dest);
    }
    success(`Updated ${commands.length} slash commands`);
  } catch (e) {
    console.error('\x1b[31m✗\x1b[0m Failed to update slash commands: ' + e.message);
    process.exit(1);
  }

  console.log('\n\x1b[32mScreenFix updated successfully!\x1b[0m\n');
  console.log('Restart Claude Code to apply changes.\n');
}

module.exports = update;
