import zipfile
import re

def search_strings(apk_path):
    with zipfile.ZipFile(apk_path, 'r') as z:
        data = z.read('AndroidManifest.xml')
        
        # Decode as UTF-16LE and UTF-8 with ignore
        text_u16 = data.decode('utf-16-le', errors='ignore')
        text_u8 = data.decode('utf-8', errors='ignore')
        
        # Merge them
        all_text = text_u16 + "\n" + text_u8
        
        # Regex to find package name formats: e.g. com.example.app
        # Allow dots and word characters
        pattern = re.compile(r'\b[a-zA-Z][a-zA-Z0-9_]*\.[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+\b')
        matches = pattern.findall(all_text)
        
        # Unique candidates
        candidates = set(matches)
        
        # Filter typical non-package patterns
        filtered = []
        for c in candidates:
            c_lower = c.lower()
            if 'android' in c_lower or 'schema' in c_lower or 'w3.org' in c_lower or 'google' not in c_lower:
                if 'karsha' in c_lower or 'pilabs' in c_lower or 'cc' in c_lower:
                    filtered.append(c)
                elif 'android' not in c_lower and 'schema' not in c_lower and 'google' not in c_lower:
                    filtered.append(c)
                    
        return sorted(list(set(filtered))), sorted(list(candidates))

if __name__ == '__main__':
    import os
    apk_dir = "uploads/apks"
    for f in os.listdir(apk_dir):
        if f.endswith('.apk') and not 'test' in f:
            path = os.path.join(apk_dir, f)
            print(f"\n--- Scanning {path} ---")
            filtered, all_candidates = search_strings(path)
            print("Filtered candidates:")
            for c in filtered:
                print("  =>", c)
            print("\nAll package-like matches:")
            print(", ".join(all_candidates[:50]))
