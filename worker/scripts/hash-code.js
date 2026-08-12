// One-off helper for seeding a contributor row.
//
//   node scripts/hash-code.js "Alice" "some-access-code"
//
// Prints a ready-to-paste `wrangler d1 execute` command that inserts the
// contributor with the correctly hashed access code (same sha256(name:code)
// scheme the Worker itself uses in src/index.js).
const crypto = require('node:crypto');

const [name, code, role] = process.argv.slice(2);
if (!name || !code) {
  console.error('Usage: node scripts/hash-code.js <name> <code> [role=contributor|owner]');
  process.exit(1);
}

const hash = crypto.createHash('sha256').update(`${name}:${code}`).digest('hex');
const safeName = name.replace(/'/g, "''");

console.log(`npx wrangler d1 execute launch-points-db --remote --command="INSERT INTO contributors (name, access_code_hash, role) VALUES ('${safeName}', '${hash}', '${role || 'contributor'}')"`);
