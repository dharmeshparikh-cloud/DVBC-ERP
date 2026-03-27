/**
 * GSTIN Validation & Extraction Utilities
 * 
 * GSTIN Format: 22AAAAA0000A1Z5 (15 characters)
 * [01-37] State Code | [10 char] PAN | [1 char] Entity | [Z] Default | [1 char] Checksum
 */

const STATE_CODE_MAP = {
  '01': 'Jammu & Kashmir',
  '02': 'Himachal Pradesh',
  '03': 'Punjab',
  '04': 'Chandigarh',
  '05': 'Uttarakhand',
  '06': 'Haryana',
  '07': 'Delhi',
  '08': 'Rajasthan',
  '09': 'Uttar Pradesh',
  '10': 'Bihar',
  '11': 'Sikkim',
  '12': 'Arunachal Pradesh',
  '13': 'Nagaland',
  '14': 'Manipur',
  '15': 'Mizoram',
  '16': 'Tripura',
  '17': 'Meghalaya',
  '18': 'Assam',
  '19': 'West Bengal',
  '20': 'Jharkhand',
  '21': 'Odisha',
  '22': 'Chhattisgarh',
  '23': 'Madhya Pradesh',
  '24': 'Gujarat',
  '25': 'Daman & Diu',
  '26': 'Dadra & Nagar Haveli',
  '27': 'Maharashtra',
  '28': 'Andhra Pradesh',
  '29': 'Karnataka',
  '30': 'Goa',
  '31': 'Lakshadweep',
  '32': 'Kerala',
  '33': 'Tamil Nadu',
  '34': 'Puducherry',
  '35': 'Andaman & Nicobar',
  '36': 'Telangana',
  '37': 'Andhra Pradesh (New)',
  '38': 'Ladakh',
  '97': 'Other Territory',
};

const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

/**
 * Validate GSTIN format and extract details
 * @param {string} gstin 
 * @returns {{ valid: boolean, stateCode: string, stateName: string, pan: string, errors: string[] }}
 */
export function validateGSTIN(gstin) {
  const result = { valid: false, stateCode: '', stateName: '', pan: '', errors: [] };

  if (!gstin) return result;

  const cleaned = gstin.toUpperCase().trim();

  if (cleaned.length !== 15) {
    result.errors.push(`Must be 15 characters (currently ${cleaned.length})`);
    return result;
  }

  if (!GSTIN_REGEX.test(cleaned)) {
    result.errors.push('Invalid GSTIN format');
    return result;
  }

  const stateCode = cleaned.substring(0, 2);
  const stateName = STATE_CODE_MAP[stateCode];

  if (!stateName) {
    result.errors.push(`Invalid state code: ${stateCode}`);
    return result;
  }

  result.valid = true;
  result.stateCode = stateCode;
  result.stateName = stateName;
  result.pan = cleaned.substring(2, 12);

  return result;
}

/**
 * Check if company name partially matches the PAN entity name in GSTIN
 * PAN chars 1-5 relate to entity name (first 5 chars of surname/org name)
 * @param {string} gstin 
 * @param {string} companyName 
 * @returns {{ match: boolean, hint: string }}
 */
export function matchGSTINCompany(gstin, companyName) {
  if (!gstin || !companyName) return { match: false, hint: '' };

  const cleaned = gstin.toUpperCase().trim();
  if (cleaned.length !== 15) return { match: false, hint: '' };

  // PAN is chars 3-12 (0-indexed: 2-11)
  const pan = cleaned.substring(2, 12);
  // 4th char of PAN indicates type: C=Company, P=Person, F=Firm, etc.
  const entityType = pan.charAt(3);
  // Chars 1-5 of PAN: first 5 chars of surname (individual) or entity name (company/firm)
  const panNameChars = pan.substring(0, 4); // First 4 of the 5-char name block

  const companyUpper = companyName.toUpperCase().replace(/[^A-Z]/g, '');

  // For company/firm (C/F/H/A/T), check if company name starts with the PAN name chars
  if (['C', 'F', 'H', 'A', 'T'].includes(entityType)) {
    // Company PAN: first 5 chars = first 5 of company name
    const panName5 = pan.substring(0, 5);
    if (companyUpper.startsWith(panName5)) {
      return { match: true, hint: `Company PAN matches: ${panName5}*` };
    }
    // Partial match (first 3 chars)
    if (companyUpper.substring(0, 3) === panName5.substring(0, 3)) {
      return { match: true, hint: `Partial match on entity name` };
    }
    return { match: false, hint: `PAN entity "${panName5}" doesn't match "${companyUpper.substring(0, 5)}"` };
  }

  // For individual (P), the name block is surname
  if (entityType === 'P') {
    return { match: false, hint: `This is a personal PAN (not a company GSTIN)` };
  }

  return { match: false, hint: '' };
}

export { STATE_CODE_MAP };
