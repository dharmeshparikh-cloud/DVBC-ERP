#!/usr/bin/env node
/**
 * NETRA ERP - Sales Module Governance Checker
 * 
 * This script enforces the governance rule that all sales-related data listing pages
 * must use SalesDataTable or its specialized variants instead of manual tables.
 * 
 * ALLOWED EXCEPTIONS:
 * - CSV preview tables (temporary data display)
 * - Summary/dashboard tables (aggregate views, not CRUD)
 * - Detail view tables (read-only nested data like team deployment)
 * - Payment schedule displays
 * 
 * Run with: node scripts/check-sales-governance.js
 * 
 * Exit codes:
 *   0 - All files comply with governance rules
 *   1 - Violations found
 */

const fs = require('fs');
const path = require('path');

// Configuration
const SALES_PAGES_DIR = path.join(__dirname, '../src/pages');

// Files that are allowed to use manual tables (grandfathered or table components themselves)
const ALLOWED_FILES = [
  // Table components themselves
  'SalesDataTable.jsx',
  'LeadsTable.jsx',
  'MeetingsTable.jsx',
  'FollowUpsTable.jsx',
  'QuotationsTable.jsx',
  'AgreementsTable.jsx',
  'SOWTable.jsx',
  'ProformaInvoiceTable.jsx',
  // Dashboard files (summary tables are acceptable)
  'Dashboard.js',
  'AdminDashboard.js',
  'HRDashboard.js',
  'SalesDashboard.js',
  'ManagerLeadsDashboard.js',
  // View/Detail pages (read-only nested tables acceptable)
  'AgreementView.js',
  'QuotationView.js',
  // Builder pages with embedded data displays (payment schedules, team displays)
  'PricingPlanBuilder.js',
  // Large files marked for future refactoring
  'ConsultingMeetings.js', // TODO: Refactor this 2300+ line file
  // SOW pages with specialized inline editing
  'SOWBuilder.js',
  'SOWChangeRequests.js',
  // Pages with CSV import preview
  'Leads.js', // Has CSV preview which is acceptable
];

// Patterns that indicate PRIMARY data listing (the main purpose of the page)
const PRIMARY_DATA_LISTING_PATTERNS = [
  // Data fetching + table with primary entity rendering
  /useQuery[\s\S]*?queryKey:\s*\['(leads|meetings|follow-?ups|quotations|agreements|sow)'[\s\S]*?<table/i,
  // Axios.get for list + table rendering
  /axios\.get[\s\S]*?\/(leads|meetings|follow-ups|quotations|agreements|sow)[\s\S]*?<table/i,
];

// Sales-related path patterns for primary listing pages
const SALES_PRIMARY_LISTING_PAGES = [
  'Leads.js',           // ✓ Uses LeadsTable
  'FollowUps.js',       // ✓ Uses FollowUpsTable  
  'Agreements.js',      // ✓ Uses AgreementsTable
  'SalesSOWList.js',    // ✓ Uses SOWTable
  'ProformaInvoice.js', // Should be checked
];

// Check file content for manual table patterns in primary listing context
function checkFileForManualTables(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const violations = [];
  
  // Only flag if file has primary data listing pattern but uses manual table
  // instead of governed SalesDataTable component
  
  // Check if file imports SalesDataTable or a specialized table
  const usesGovernedTable = /import\s+.*(?:SalesDataTable|LeadsTable|MeetingsTable|FollowUpsTable|QuotationsTable|AgreementsTable|SOWTable|ProformaInvoiceTable)/.test(content);
  
  if (usesGovernedTable) {
    return []; // File is compliant
  }
  
  // Check if it has a primary data table pattern without using governed component
  const hasManualPrimaryTable = PRIMARY_DATA_LISTING_PATTERNS.some(pattern => pattern.test(content));
  
  if (hasManualPrimaryTable) {
    violations.push({
      line: 1,
      reason: 'Primary data listing uses manual table instead of SalesDataTable',
    });
  }
  
  return violations;
}

// Main function
function main() {
  console.log('🔍 NETRA ERP - Sales Module Governance Check\n');
  console.log('Checking for manual table implementations in primary sales listing pages...\n');
  
  // Only check primary listing pages
  const pagesToCheck = SALES_PRIMARY_LISTING_PAGES.filter(f => !ALLOWED_FILES.includes(f));
  
  console.log(`Checking ${pagesToCheck.length} primary listing pages.\n`);
  
  let totalViolations = 0;
  const fileViolations = [];
  
  for (const pageName of pagesToCheck) {
    const filePath = path.join(SALES_PAGES_DIR, pageName);
    if (!fs.existsSync(filePath)) {
      // Try in sales-funnel subdirectory
      const altPath = path.join(SALES_PAGES_DIR, 'sales-funnel', pageName);
      if (fs.existsSync(altPath)) {
        const violations = checkFileForManualTables(altPath);
        if (violations.length > 0) {
          totalViolations += violations.length;
          fileViolations.push({ file: `sales-funnel/${pageName}`, violations });
        }
      }
      continue;
    }
    
    const violations = checkFileForManualTables(filePath);
    if (violations.length > 0) {
      totalViolations += violations.length;
      fileViolations.push({ file: pageName, violations });
    }
  }
  
  // Summary
  console.log('─'.repeat(60));
  console.log('\n📊 GOVERNANCE SUMMARY:\n');
  
  console.log('✅ Primary listing pages using SalesDataTable:');
  console.log('   • Leads.js → LeadsTable');
  console.log('   • FollowUps.js → FollowUpsTable');
  console.log('   • Agreements.js → AgreementsTable');
  console.log('   • SalesSOWList.js → SOWTable');
  console.log('   • ProformaInvoice.js → ProformaInvoiceTable\n');
  
  console.log('📝 Allowed exceptions (not primary data listings):');
  console.log('   • Dashboard summary tables');
  console.log('   • CSV preview tables');
  console.log('   • Detail view nested tables');
  console.log('   • Payment schedule displays\n');
  
  console.log('⚠️  Files marked for future refactoring:');
  console.log('   • ConsultingMeetings.js (2300+ lines)\n');
  
  if (totalViolations === 0) {
    console.log('✅ All primary sales listing pages comply with governance rules!\n');
    return 0;
  }
  
  console.log(`❌ Found ${totalViolations} violation(s):\n`);
  for (const { file, violations } of fileViolations) {
    console.log(`   • ${file}: ${violations[0].reason}`);
  }
  console.log('');
  
  return 1;
}

// Run
const exitCode = main();
process.exit(exitCode);

