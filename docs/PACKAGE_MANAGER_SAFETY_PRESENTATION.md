# Datya Linux Package Manager and Safety Presentation Script

## Slide 1 — Datya Linux: Freedom with Security

नमस्कार। Datya Linux का लक्ष्य केवल बहुत सारे security tools को एक जगह जमा करना नहीं है। हमारा लक्ष्य ऐसा Linux बनाना है जो तेज़, शक्तिशाली, privacy-first और user-controlled हो। User को यह महसूस होना चाहिए कि computer उसका अपना है—किसी ने उसे कैद नहीं किया है।

## Slide 2 — समस्या

आज security tools install करना कठिन हो सकता है। Packages अलग-अलग sources से आते हैं, dependencies टूट सकती हैं, malicious या tampered files का risk रहता है, और कई बार user को पता ही नहीं चलता कि कोई command कितनी files, services या permissions बदल देगी। Live stream या online chat में कोई व्यक्ति user से एक dangerous command चलवा सकता है और data हट सकता है।

Datya इस समस्या का उत्तर transparency, verification, isolation और informed confirmation से देगा।

## Slide 3 — Modular ecosystem

Datya का package manager modular होगा। Base operating system छोटा और stable रहेगा। Tools अलग capability packs में आएँगे—network diagnostics, defense, forensics, privacy, reverse engineering, wireless, cloud security, cryptography, learning labs और developer tools।

इससे user केवल वही install करेगा जिसकी उसे आवश्यकता है। Tool हटाना, बदलना, update रोकना या alternative package चुनना भी user के control में रहेगा।

## Slide 4 — Lifecycle

हर capability का lifecycle स्पष्ट होगा:

```text
catalogued → verified → packaged → installed → tested → profile-available → enabled-by-user
```

Installed package automatically running नहीं होगा। Profile enable करने से कोई scan या hidden background command शुरू नहीं होगी। User को package, profile और execution के बीच साफ़ अंतर दिखाई देगा।

## Slide 5 — Package verification

Install से पहले Datya source URL, signed repository metadata, trusted key, architecture, exact artifact checksum, dependency graph, maintainer scripts, requested services, privileges, setuid bits, device access और network behavior verify करेगा।

हम यह दावा नहीं करेंगे कि कोई malware scanner हर malicious package को पकड़ सकता है। Security honest होगी। User को trust level दिखेगा: verified, metadata-verified या community/experimental। Checksum mismatch या unsigned source पर default transaction रुक जाएगा और failure का कारण साफ़ दिखेगा।

## Slide 6 — Install plan

User को केवल “Install package?” नहीं दिखेगा। Datya plan में बताएगा कि कौन-सी files आएँगी, कौन-सी dependencies जुड़ेंगी, कौन-सी services शुरू हो सकती हैं, कितना disk space लगेगा, कौन-सा privilege चाहिए, network behavior क्या है और rollback available है या नहीं।

Plan text या JSON में export किया जा सकेगा ताकि user independently review कर सके।

## Slide 7 — High-security sandbox

Unknown scripts और risky tools के लिए Datya sandbox profiles देगा। Safe profile read-only system view, temporary workspace, disabled network और CPU, memory, process, timeout तथा output limits लगाएगा। Project profile केवल चुने हुए project files दिखाएगा। Lab profile explicit lab network और disposable environment के लिए होगा।

यदि Bubblewrap या दूसरा isolation backend उपलब्ध नहीं है, safe profile host पर silently execute नहीं होगा—वह fail closed होगा। Power User profile अलग और explicit होगा, जहाँ experienced administrator normal Linux control इस्तेमाल कर सकेगा।

## Slide 8 — User freedom

Security का अर्थ user को हर command से रोकना नहीं है। Datya में user अपनी machine पर commands, packages, services, policies, themes, repositories और cryptographic settings customize कर सकेगा।

Power User mode में कोई hidden sandbox नहीं होगा। Workbench केवल risk, privilege और network impact समझाएगा। User policy बदल सकेगा, लेकिन हर important decision visible और reversible रखने का प्रयास होगा।

## Slide 9 — Destructive command protection

Remove, purge, recursive dependency cleanup, key deletion, configuration reset और filesystem cleanup high-impact actions माने जाएँगे। पहले impact preview होगा। इसमें exact files, shared dependencies, services, profiles और rollback दिखेगा।

दूसरे prompt में user को exact package या target name type करना होगा। केवल Enter दबाने से deletion नहीं होगा। यह design accidental commands और live-stream social engineering दोनों के विरुद्ध सुरक्षा देता है।

## Slide 10 — No copied-command trust

किसी chat, website या live-stream viewer का command trusted authorization नहीं माना जाएगा। Dangerous shell patterns जैसे `curl | sh`, obfuscated commands, broad globs और recursive deletes का readable expansion दिखाया जाएगा।

User command को inspect, cancel, export या rollback कर सकेगा। Headless automation में destructive actions default-disabled रहेंगे और explicit policy file तथा audit record आवश्यक होगा।

## Slide 11 — Audit and recovery

हर install, update, remove, verification failure और policy override का local transaction record बनेगा। State snapshot में package graph, changed files, profile changes और rollback availability होगी।

Rollback user evidence को silently erase नहीं करेगा। Datya का उद्देश्य केवल system को वापस करना नहीं, बल्कि यह भी बताना है कि क्या बदला था और कब बदला था।

## Slide 12 — Road ahead

पहले हम read-only catalog, package information और transaction plans को मजबूत करेंगे। फिर verified install/remove engine, dependency resolver, profile manager, Rust state library, rollback, Security Center integration और community catalog जोड़ेंगे।

हर चरण में code, tests, verification, benchmarks और documentation साथ चलेंगे।

## Closing — Datya promise

Datya Linux का promise है:

> **तुम्हारी machine, तुम्हारा control—लेकिन हर important action साफ़, verified और समझने योग्य।**

हम Kali से अधिक tools जोड़ना चाहते हैं, लेकिन बिना अंधे package dumping के। हम ऐसा ecosystem बनाएँगे जो व्यापक भी हो, modular भी हो, तेज़ भी हो, और trustworthy भी। Datya user को रोकने के लिए नहीं, user को सक्षम बनाने के लिए बनेगा।
