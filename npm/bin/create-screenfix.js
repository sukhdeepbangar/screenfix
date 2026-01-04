#!/usr/bin/env node

const { program } = require('commander');
const init = require('../lib/init');
const doctor = require('../lib/doctor');
const uninstall = require('../lib/uninstall');
const update = require('../lib/update');

program
  .name('create-screenfix')
  .description('ScreenFix - Screenshot capture tool for Claude Code')
  .version('0.1.0');

program
  .command('init')
  .description('Initialize ScreenFix in the current project')
  .option('--skip-python', 'Skip Python dependency installation')
  .action(init);

program
  .command('doctor')
  .description('Check ScreenFix installation and diagnose issues')
  .action(doctor);

program
  .command('uninstall')
  .description('Remove ScreenFix from the current project')
  .action(uninstall);

program
  .command('update')
  .description('Update ScreenFix to the latest version')
  .action(update);

// Default action: run init when called without subcommand
if (process.argv.length === 2) {
  init({});
} else {
  program.parse();
}
