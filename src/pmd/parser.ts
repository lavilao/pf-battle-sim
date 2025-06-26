// Main parser for individual monster HTML pages from aonprd.com
// This will be a translation of src/pathfinder_combat_simulator/pmd/main.py

import { DOMParser, Element, HTMLDocument, Node, Text } from "https://deno.land/x/deno_dom/deno-dom-wasm.ts";

// From main.py:
// include3_5 = True (default)
const include3_5 = true;

const SIZES = ['Fine', 'Diminutive', 'Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan', 'Colossal'];
const ASTERISK_OPTIONS = ["**", "*", "†"]; // Should put things like ** before * for regex matching

// Global class hit dice data - will be loaded from pmd_data/class_hds.json
let CLASS_HDS: Record<string, number | null> = {};
let CLASSNAME_MAP: Record<string, string> = {};


// Helper function to log assertion failures (from Python's soft_assert)
function softAssert(condition: unknown, message: string = "Assertion failed", url: string = ""): boolean {
  if (!condition) {
    const fullMessage = `SOFT ASSERT FAILED (URL: ${url || 'N/A'}): ${message}`;
    console.warn(fullMessage);
    // Optionally, could throw an error here if strict parsing is needed or log to a file.
    // For now, just console.warn to mimic Python's behavior of logging and continuing.
    return false;
  }
  return true;
}

// Helper from Python: parseInt
function parseIntHelper(s: string, stringIfFail: boolean = false): number | string {
    const str = s.trim().replace(/,/g, "").replace("+ ", "+").replace("- ", "-");
    try {
        const num = parseInt(str, 10);
        if (isNaN(num) && stringIfFail) return s.trim();
        if (isNaN(num)) throw new Error(`Not a number: ${s}`); // Or return a specific value like 0 or NaN
        return num;
    } catch (e) {
        if (stringIfFail) return s.trim();
        throw e; // Re-throw if not stringIfFail
    }
}


// Helper from Python: splitP - split on separator while avoiding splitting on commas inside parens
function splitP(s: string, handleAnd: boolean = false, sepRegexStr: string = ', '): string[] {
    // JavaScript RegExp doesn't support arbitrary lookbehinds needed for direct translation of (?![^()]*\))
    // This is a simplified version. May need more robust handling for complex cases.
    // A common approach for this in JS is iterative matching or more complex regex.
    // For now, a simple split by the separator string. If it's just a comma, it's easier.
    // The Python regex was: sep + r'(?![^()]*\)|[^\[\]]*\])'
    // This is tricky. For now, let's assume simple comma separation or explicit ' or '
    if (sepRegexStr === ', ' && s.includes('(') && s.includes(')')) {
        // Basic handling: if we see parens, we might need a more complex split.
        // This is a placeholder for a more robust solution if needed.
        // For many cases, a direct split by comma or " or " will work.
    }

    let parts = s.split(new RegExp(sepRegexStr));
    if (handleAnd && parts.length > 0) {
        const lastPart = parts[parts.length - 1].trim();
        if (lastPart.toLowerCase().startsWith("and ")) {
            parts[parts.length - 1] = lastPart.substring(4).trim();
        }
    }
    return parts.map(p => p.trim()).filter(p => p);
}

// Helper from Python: unwrapParens
function unwrapParens(s: string): string {
    s = s.trim();
    if (s.startsWith("(") && s.endsWith(")")) {
        return s.substring(1, s.length - 1).trim();
    }
    return s;
}

// Helper from Python: cleanS
function cleanS(s: string, trailingChar: string = ";"): string {
    s = s.trim();
    if (s.endsWith(trailingChar)) {
        s = s.substring(0, s.length - 1);
    }
    return s.trim();
}

// Helper from Python: handleAsterisk
function handleAsterisk(s: string): string {
    let tempS = s;
    for (const ast of ASTERISK_OPTIONS) { // Ensure longer ones are replaced first if they are substrings
        const astRegex = new RegExp(ast.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
        tempS = tempS.replace(astRegex, '');
    }
    return tempS.trim();
}


// Placeholder for the main parsing function
export function parsePage(htmlContent: string, url: string): Record<string, any> | null {
    const pageObject: Record<string, any> = {};

    // Clean up HTML (regex part from Python)
    // Python: regex = r'(?:\r\n|\r|\xad|' + chr(10) + ')+'
    // JS: const weirdWhitespaceRegex = /(?:\r\n|\r|\xad|\n)+/g; // \n covers chr(10)
    // Python: html = re.sub(r'(?<=\s+)' + regex + r'|' + regex + r'(?=\s+)', r'', html)
    // JS: htmlContent = htmlContent.replace(/(\s+)(?:\r\n|\r|\xad|\n)+|(?:\r\n|\r|\xad|\n)+(\s+)/g, '$1$2'); // Simplified, might need refinement
    // Python: html = re.sub(regex, r' ', html)
    // JS: htmlContent = htmlContent.replace(/(?:\r\n|\r|\xad|\n)+/g, ' ');
    // Python: html = re.sub(r'(?<!<\s*br\s*>\s*)<\s*/\s*br\s*>', r'<br/>', html) // Variable-width negative lookbehind
    // JS: This is hard. JS RegExp has limited lookbehind. May need to handle broken <br> tags differently or simplify.
    // For now, let's assume deno-dom handles some of this.
    // Python: html = re.sub(r'<\s*/?\s*br\s*/?\s*>', r'<br/>', html)
    // JS: htmlContent = htmlContent.replace(/<\s*\/?>\s*br\s*\/?>/gi, '<br/>');
    // Python: html = re.sub(r'[−—–‐‑‒―]|&ndash;|&mdash;', "-", html)
    // JS: htmlContent = htmlContent.replace(/[−—–‐‑‒―]|&ndash;|&mdash;/g, "-");
    // Python: html = re.sub(r'’', r"'", html)
    // JS: htmlContent = htmlContent.replace(/’/g, "'");

    // The regex replacements in Python are quite specific. Direct translation is complex.
    // deno-dom might normalize some of this. We'll apply simpler regex for now and adjust.
    htmlContent = htmlContent.replace(/[−—–‐‑‒―]|&ndash;|&mdash;/g, "-");
    htmlContent = htmlContent.replace(/’/g, "'");
    // Normalize line breaks before parsing for consistency, but be careful not to break <pre> or similar.
    // For stat blocks, multiple spaces/newlines are often condensed.
    htmlContent = htmlContent.replace(/\r\n|\r/g, '\n');


    const soup = new DOMParser().parseFromString(htmlContent, "text/html");
    if (!soup) {
        console.error("Failed to parse HTML for URL: " + url);
        return null;
    }

    // The Python code selects "#main table tr td span" and then iterates its .contents
    // This is a very specific selector.
    // In AoNPRD, this is often the main content area for monsters.
    const mainContainer = soup.querySelector("div#main table tr td span");

    if (!mainContainer) {
        console.warn(`Could not find main content span (div#main table tr td span) for ${url}`);
        return null;
    }

    // Convert NodeList to a plain array for easier manipulation (like Python's list `e`)
    // We need to handle Text nodes and Element nodes carefully.
    // The Python code iterates over `e.contents` which is a list of children.
    // We'll create a custom iterator or process nodes one by one.

    let currentIndex = 0;
    const nodes = Array.from(mainContainer.childNodes);

    // Helper to get current node and advance
    const nextNode = (skipWhitespaceText = true): Node | null => {
        while (skipWhitespaceText && currentIndex < nodes.length) {
            const node = nodes[currentIndex];
            if (node.nodeType === Node.TEXT_NODE && (node as Text).textContent.trim() === "") {
                currentIndex++;
                continue;
            }
            break;
        }
        if (currentIndex < nodes.length) {
            return nodes[currentIndex++];
        }
        return null;
    };

    const peekNode = (skipWhitespaceText = true, offset = 0): Node | null => {
        let tempIndex = currentIndex + offset;
        while (skipWhitespaceText && tempIndex < nodes.length) {
            const node = nodes[tempIndex];
            if (node.nodeType === Node.TEXT_NODE && (node as Text).textContent.trim() === "") {
                tempIndex++;
                continue;
            }
            break;
        }
        return tempIndex < nodes.length ? nodes[tempIndex] : null;
    };

    // Helper to skip <br> tags, similar to Python's skipBr
    const skipBr = (optional = false): boolean => {
        const node = peekNode(true); // Don't advance yet, just peek
        if (node && node.nodeType === Node.ELEMENT_NODE && (node as Element).tagName === "BR") {
            currentIndex++; // Consume the <br>
            // Skip potential whitespace text node after <br>
            const afterBr = peekNode(true);
            if (afterBr && afterBr.nodeType === Node.TEXT_NODE && afterBr.textContent.trim() === "") {
                 currentIndex++;
            }
            return true;
        }
        if (!optional && !(node && node.nodeType === Node.ELEMENT_NODE && (node as Element).tagName === "BR")) {
            softAssert(false, `Expected <br> but found ${node?.nodeName}`, url);
        }
        return false;
    };

    // Helper to collect text until a specific tag or end
    // Python's collectText was complex. This is a simplified start.
    const collectTextUntil = (stopTagNames: string[], includeStopTagText: boolean = false): string => {
        let text = "";
        while (true) {
            const node = peekNode(false); // Get current node without skipping initial whitespace text
            if (!node) break;

            if (node.nodeType === Node.ELEMENT_NODE) {
                const el = node as Element;
                if (stopTagNames.includes(el.tagName)) {
                    if (includeStopTagText) text += el.textContent;
                    break;
                }
                if (el.tagName === "BR") {
                    text += "\n";
                } else {
                    text += el.textContent; // Potentially recursive if complex nodes
                }
            } else if (node.nodeType === Node.TEXT_NODE) {
                text += (node as Text).textContent;
            }
            nextNode(false); // Consume the node we just processed
        }
        return text.trim();
    };

    // --- Start Parsing Sections ---

    // Skip preamble (Python: while not (e[i].name == "h1" and ...))
    // This logic needs to be adapted to the node iteration
    while(true) {
        const node = peekNode(true);
        if (!node) { console.warn("Reached end of nodes while skipping preamble for " + url); return null; }
        if (node.nodeType === Node.ELEMENT_NODE) {
            const el = node as Element;
            if (el.tagName === "H1") {
                const nextEl = peekNode(true, 1); // Peek next significant node
                if (nextEl && nextEl.nodeType === Node.ELEMENT_NODE) {
                    const nextElTag = (nextEl as Element).tagName;
                    if (nextElTag === "H2" || (nextElTag === "I" && peekNode(true, 2)?.nodeName === "H2")) {
                        break; // Found the start pattern
                    }
                }
            }
        }
        nextNode(true); // Consume and continue
    }


    // Get main title (H1 tag)
    let currentNode = nextNode(true); // Consume H1
    if (currentNode && currentNode.nodeType === Node.ELEMENT_NODE && (currentNode as Element).tagName === "H1" && (currentNode as Element).classList.contains("title")) {
        pageObject["title1"] = (currentNode as Element).textContent.trim();
        if ((currentNode as Element).querySelector("img[src='images\\ThreeFiveSymbol.gif']")) {
            pageObject["is_3.5"] = true;
        }
    } else {
        softAssert(false, "Could not find H1 title.", url);
        return null;
    }

    // Get short description (optional I tag)
    currentNode = peekNode(true);
    if (currentNode && currentNode.nodeType === Node.ELEMENT_NODE && (currentNode as Element).tagName === "I") {
        pageObject["desc_short"] = (currentNode as Element).textContent.trim();
        nextNode(true); // Consume I tag
    }

    // Get statblock title & CR (H2 tag)
    currentNode = nextNode(true); // Consume H2
    if (currentNode && currentNode.nodeType === Node.ELEMENT_NODE && (currentNode as Element).tagName === "H2" && (currentNode as Element).classList.contains("title")) {
        const h2Text = (currentNode as Element).textContent.trim();
        const crRegex = /^(.*)\s+CR\s+([0-9/-]+)(?:\/MR\s+(\d+))?$/;
        const match = h2Text.match(crRegex);
        if (match) {
            pageObject["title2"] = match[1].trim();
            const crStr = match[2];
            if (crStr === "-") {
                pageObject["CR"] = null;
            } else if (crStr.includes("/")) {
                const [num, den] = crStr.split("/").map(Number);
                pageObject["CR"] = num && den ? num / den : crStr; // Store as fraction or original string if invalid
            } else {
                pageObject["CR"] = parseFloat(crStr);
            }
            if (match[3]) {
                pageObject["MR"] = parseInt(match[3], 10);
            }
        } else {
            softAssert(false, `CR-finding Regex failed for H2: "${h2Text}"`, url);
            pageObject["title2"] = h2Text; // Store full text if regex fails
        }
    } else {
        softAssert(false, "Could not find H2 statblock title.", url);
        return null;
    }

    // Get sources (B tag "Source" followed by A tags)
    currentNode = nextNode(true); // Consume B "Source"
    if (!(currentNode && currentNode.nodeType === Node.ELEMENT_NODE && (currentNode as Element).tagName === "B" && (currentNode as Element).textContent.trim() === "Source")) {
        softAssert(false, "Expected 'Source' B tag.", url);
    } else {
        nextNode(true); // Consume the text node after "Source " (usually a space)

        pageObject["sources"] = [];
        while(true) {
            currentNode = peekNode(true);
            if (currentNode && currentNode.nodeType === Node.ELEMENT_NODE && (currentNode as Element).tagName === "A") {
                const linkElement = currentNode as Element;
                const sourceText = linkElement.textContent.trim();
                const sourceRegex = /^(.*?)\s+pg\.\s+(\d+)$/;
                const match = sourceText.match(sourceRegex);
                if (match) {
                    pageObject["sources"].push({
                        name: match[1].trim(),
                        page: parseInt(match[2], 10),
                        link: linkElement.getAttribute("href")?.trim() || ""
                    });
                } else {
                    softAssert(false, `Source text format error: "${sourceText}"`, url);
                }
                nextNode(true); // Consume A tag

                // Skip comma text node if present
                const commaNode = peekNode(false); // Don't skip whitespace to catch immediate comma
                if (commaNode && commaNode.nodeType === Node.TEXT_NODE && commaNode.textContent.trim().startsWith(",")) {
                    nextNode(false); // Consume comma node
                }
            } else {
                break; // No more A tags
            }
        }
        if (pageObject["sources"].length === 0) {
            softAssert(false, "No sources found after 'Source' tag.", url);
        }
    }
    skipBr();


    // Get XP (optional B tag "XP")
    currentNode = peekNode(true);
    if (currentNode && currentNode.nodeType === Node.ELEMENT_NODE && (currentNode as Element).tagName === "B" && (currentNode as Element).textContent.trim() === "XP") {
        nextNode(true); // Consume B "XP"
        const xpTextNode = nextNode(false); // Get the text node containing XP value
        if (xpTextNode && xpTextNode.nodeType === Node.TEXT_NODE) {
            const xpText = handleAsterisk(xpTextNode.textContent.trim());
            if (xpText === "" || xpText === "-") {
                pageObject["XP"] = null;
            } else {
                pageObject["XP"] = parseIntHelper(xpText, true); // Use stringIfFail true for robustness
            }
        } else {
            softAssert(false, "XP value not found after 'XP' B tag.", url);
        }
        skipBr();
    }

    // TODO: Race/Class, Alignment/Size/Type, Init, Senses, Aura sections
    // This will require careful iteration and regex matching similar to the Python script.

    pageObject["_parser_status"] = "basique en-tête analysé";


    if (!include3_5 && pageObject["is_3.5"] === true) {
        return null; // Skip 3.5e entries if configured
    }

    return pageObject;
}


// Main function to orchestrate reading HTML files and parsing them
export async function runParser(htmlDir: string, urlsPath: string, brokenUrlsPath: string, classHDsPath: string, outputPath: string): Promise<void> {
    console.log("Starting monster data parsing...");

    try {
        const classHdsJson = await Deno.readTextFile(classHDsPath);
        CLASS_HDS = JSON.parse(classHdsJson);
        CLASSNAME_MAP = {};
        for (const className of Object.keys(CLASS_HDS)) {
            CLASSNAME_MAP[className.toLowerCase()] = className;
        }
        console.log(`Loaded ${Object.keys(CLASS_HDS).length} class HD entries.`);
    } catch (e) {
        console.error(`Failed to load class_hds.json from ${classHDsPath}: ${e.message}`);
        console.error("Please ensure getClasses.ts has been run successfully.");
        return;
    }

    let urls: string[];
    try {
        urls = (await Deno.readTextFile(urlsPath)).split('\n').map(u => u.trim()).filter(u => u);
    } catch (e) {
        console.error(`Failed to read URLs from ${urlsPath}: ${e.message}`);
        return;
    }

    let brokenUrls: string[] = [];
    try {
        brokenUrls = (await Deno.readTextFile(brokenUrlsPath))
            .split('\n')
            .map(u => u.trim())
            .filter(u => u && !u.startsWith("#"));
    } catch (e) {
        if (!(e instanceof Deno.errors.NotFound)) {
            console.warn(`Could not read broken_urls.txt from ${brokenUrlsPath}: ${e.message}`);
        }
        // If not found, it's fine, just means no pre-defined broken URLs.
    }
    const brokenUrlsSet = new Set(brokenUrls);

    const allPageObjects: Record<string, any> = {};
    let successCount = 0;
    let errorCount = 0;
    let skipCount = 0;

    // Helper to get MD5 for filename consistency with downloadPages.ts
    async function getMD5(text: string): Promise<string> {
        const encoder = new TextEncoder();
        const data = encoder.encode(text);
        const hashBuffer = await crypto.subtle.digest('MD5', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    console.log(`Parsing ${urls.length} HTML files from ${htmlDir}...`);
    // const progressBar = популярный(urls, { title: "Parsing HTML" }); // If tqdm is desired

    for (const url of urls) { // Replace progressBar with urls for direct iteration if tqdm causes issues
        if (brokenUrlsSet.has(url)) {
            // console.log(`Skipping pre-marked broken URL: ${url}`);
            skipCount++;
            continue;
        }

        const filename = await getMD5(url) + ".html";
        const filepath = `${htmlDir}/${filename}`;

        try {
            const htmlContent = await Deno.readTextFile(filepath);
            const parsedData = parsePage(htmlContent, url); // Call the (yet to be fully implemented) parser

            if (parsedData) {
                if (parsedData["_parser_status"] !== "partiellement implémenté" || Object.keys(parsedData).length > 2) {
                     allPageObjects[url] = parsedData;
                     successCount++;
                } else {
                    // console.warn(`Parser only partially implemented for ${url}, skipping output for now.`);
                    // errorCount++; // Or a different counter for partially parsed
                }
            } else {
                // parsePage might return null for 3.5e content or actual parsing errors
                if (include3_5 || !(htmlContent.includes("images\\ThreeFiveSymbol.gif")) ) { // crude check
                     console.warn(`Parsing returned null for ${url}, possibly an error or skipped 3.5 content.`);
                     errorCount++;
                } else {
                    skipCount++; // Skipped 3.5
                }
            }
        } catch (e) {
            console.error(`Error processing file ${filepath} for URL ${url}: ${e.message}`);
            if (e.stack) console.error(e.stack);
            errorCount++;
        }
        // progressBar.update(); // If using tqdm
    }
    // progressBar.close(); // If using tqdm

    console.log(`Parsing complete. Success: ${successCount}, Errors: ${errorCount}, Skipped: ${skipCount}.`);

    try {
        await Deno.writeTextFile(outputPath, JSON.stringify(allPageObjects, null, 2));
        console.log(`Successfully wrote parsed monster data to ${outputPath}`);
    } catch (e) {
        console.error(`Error writing parsed data to ${outputPath}: ${e.message}`);
    }
}

// Example of how to run it (adjust paths as needed)
// if (import.meta.main) {
//   runParser(
//     "pmd_data/html",          // Directory with downloaded HTML files
//     "pmd_data/urls.txt",      // List of URLs that were downloaded
//     "pmd_data/broken_urls.txt", // List of URLs to ignore (can be initially empty)
//     "pmd_data/class_hds.json",// Class hit dice data
//     "pmd_data/parsed_monsters.json" // Output file
//   ).catch(err => {
//     console.error("Unhandled error in runParser:", err);
//   });
// }
