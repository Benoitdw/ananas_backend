# BioPark Charleroi — suivi de l'import

Les 137 membres et partenaires de <https://www.biopark.be/community>, importes
dans `data/biopark.csv` (source `biopark`) et charges par `python -m ananas.seed`.
Les 20 fiches deja presentes dans `partners.csv` / `biotech-belgique.csv` ont
ete ecartees a l'import (liste en fin de fichier).

Etape suivante : brancher les scrapers. Convention inchangee — `key` du scraper
= `slug` de l'entreprise, liage par `python -m ananas.seed --link-only`.

Colonnes : **site** = site officiel connu, **carr.** = page carrieres reperee,
**scraper** = module ecrit et branche.

## Import

- [x] Extraction des 157 fiches `/community/` (nom, type, core business,
      taille, adresse, site, logo, description)
- [x] Dedoublonnage contre `partners.csv` + `biotech-belgique.csv` (20 ecartees)
- [x] Ecriture de `data/biopark.csv` (137 lignes) et ajout a `DEFAULT_CSVS`
- [x] Geocodage Nominatim (`python -m ananas.geocode_csv data/biopark.csv`) :
      125/137 placees
- [x] `python -m ananas.seed` : 137 creees, 267 entreprises en base
- [ ] Reperer les pages carrieres (colonne **carr.**)
- [ ] Ecrire les scrapers, par ordre de volume d'offres

## Entreprises importees

### Bank & Investment (3)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `50-north-ventures` | 50° NORTH VENTURES | Investment fund | [site](https://www.50north.vc/) | [ ] | [ ] |
| `belfius-namur-hainaut-sud` | Belfius Namur-Hainaut Sud | Service provider | [site](https://belfius-nhs.be/) | [ ] | [ ] |
| `sambrinvest` | Sambrinvest | Investment fund | — | [ ] | [ ] |

### Biologistics (2)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `ajimex` | Ajimex | Service provider | — | [ ] | [ ] |
| `chu-tivoli` | CHU Tivoli | Service provider | [site](https://www.chu-tivoli.be/) | [ ] | [ ] |

### Business & Innovation Networks (5)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `agoria` | Agoria | Public/Non-profit organisation | [site](http://www.agoria.be/) | [ ] | [ ] |
| `awex` | AWEx | Public/Non-profit organisation | [site](https://www.awex.be/) | [ ] | [ ] |
| `cci-france-belgique` | CCI France Belgique | Service provider | [site](https://www.ccifrancebelgique.be/) | [ ] | [ ] |
| `charleroi-entreprendre` | Charleroi Entreprendre | Public/Non-profit organisation | [site](http://www.charleroi-entreprendre.be/) | [ ] | [ ] |
| `essenscia` | Essenscia | Public/Non-profit organisation | [site](https://www.essenscia.be/fr/) | [ ] | [ ] |

### Centre de recherche (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `laboratoire-de-biotechnologie-vegetale-lbv` | Laboratoire de Biotechnologie Végétale (LBV) | Research Center | [site](https://cvchercheurs.ulb.ac.be/Site/unite/ULB151.php) | [ ] | [ ] |

### Cleanroom (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `airwater-labs` | AirWater Labs | Company | [site](https://awlabs.eu/%20) | [ ] | [ ] |

### CMO/CDMO (3)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `ardena-holdings` | Ardena Holdings | Company | [site](https://ardena.com/) | [ ] | [ ] |
| `bepharbel` | Bepharbel | Company | [site](https://www.bepharbel.com/en/) | [ ] | [ ] |
| `h-h-pharmaceuticals` | H&H PHARMACEUTICALS | Company | [site](https://www.hhpharma.com/) | [ ] | [ ] |

### Consulting (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `cszbio` | CSZBIO | Company | [site](https://www.linkedin.com/company/cszbio/?originalSubdomain=be) | [ ] | [ ] |

### Contract research organization (8)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `cellcarta` | CellCarta | Company | [site](https://cellcarta.com/fr/) | [ ] | [ ] |
| `center-for-microscopy-and-molecular-imaging-cmmi` | Center for Microscopy and Molecular imaging (CMMI) | Research Center | [site](https://www.cmmi.be/) | [ ] | [ ] |
| `euroscreenfast` | EuroscreenFast | Company | [site](http://www.euroscreenfast.com/) | [ ] | [ ] |
| `iqvia-laboratories` | IQVIA Laboratories | Company | [site](https://labs.iqvia.com/insights/brochure-invitro-immunology-immunogenicity) | [ ] | [ ] |
| `quality-assistance` | QUALITY ASSISTANCE | Company | [site](http://www.quality-assistance.com/) | [ ] | [ ] |
| `seqalis` | Seqalis | Company | [site](https://www.seqalis.com) | [ ] | [ ] |
| `spectralys-biotech` | Spectralys Biotech | Company | [site](http://www.spectralysbiotech.com/) | [ ] | [ ] |
| `synabs-innovative-antibodies` | SYnAbs - Innovative Antibodies | Company | [site](https://www.synabs.be/custom-monoclonal-antibody-development/) | [ ] | [ ] |

### Design & Product Development (2)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `hypnovr` | HypnoVR | Company | [site](http://hypnovr.io/) | [ ] | [ ] |
| `neuvasq` | Neuvasq | Company | — | [ ] | [ ] |

### Diagnostic (6)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `a-ulab` | A-ULAB | Company | [site](https://www.a-ulab.com/) | [ ] | [ ] |
| `institute-of-pathology-and-genetics-ipg` | Institute of Pathology and Genetics (IPG) | Research Center | [site](http://www.ipg.be/) | [ ] | [ ] |
| `oncodna` | OncoDNA | Company | [site](https://oncodna.com/) | [ ] | [ ] |
| `oneliif` | OneLiiF | Company | [site](https://www.oneliif.com/) | [ ] | [ ] |
| `superbranche` | SUPERBRANCHE | Company | [site](https://www.superbranche.com/) | [ ] | [ ] |
| `synlab-belgium` | Synlab Belgium | Company | [site](https://www.synlab.be/) | [ ] | [ ] |

### Digital health (3)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `ai4nursing` | AI4Nursing | Company | — | [ ] | [ ] |
| `allyfe` | Allyfe | Company | — | [ ] | [ ] |
| `sanaitio` | Sanaitio | Company | [site](https://sanaitio.com/) | [ ] | [ ] |

### Drug Development (28)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `3d-fibroscreen` | 3D Fibroscreen | Company | — | [ ] | [ ] |
| `aboleris-pharma` | AbolerIS Pharma | Company | [site](https://aboleris-pharma.com/) | [ ] | [ ] |
| `adipopharma` | Adipopharma | Company | [site](https://adipopharma.com/) | [ ] | [ ] |
| `aquilon-pharmaceuticals` | Aquilon Pharmaceuticals | Company | [site](https://aquilonpharma.com/en/) | [ ] | [ ] |
| `atmos-r` | Atmos R | Incubation | [site](https://atmosr.com/) | [ ] | [ ] |
| `bioxodes` | Bioxodes | Company | [site](https://bioxodes.com/) | [ ] | [ ] |
| `cancer-state-therapeutics` | Cancer State Therapeutics | Company | — | [ ] | [ ] |
| `elkedonia-belgium` | Elkedonia Belgium | Company | [site](https://elkedonia.com/) | [ ] | [ ] |
| `enodia-therapeutics` | Enodia Therapeutics | Company | [site](https://www.enodiatx.com/) | [ ] | [ ] |
| `epics-therapeuthics` | Epics Therapeuthics | Company | [site](https://www.epicstherapeutics.com/) | [ ] | [ ] |
| `equaly` | Equaly | Company | [site](https://equaly.be/index.html) | [ ] | [ ] |
| `genflow-bioscience` | Genflow Bioscience | Company | [site](http://www.genflowbio.com/) | [ ] | [ ] |
| `hemastatx` | Hemastatx | Company | [site](https://www.hemastatx.com/) | [ ] | [ ] |
| `hephaistos` | HEPHAISTOS | Company | [site](https://hephaistos-pharma.fr/) | [ ] | [ ] |
| `inchin-therapeutics` | Inchin Therapeutics | Company | [site](http://inchinntherapeutics.com/) | [ ] | [ ] |
| `mileutis` | Mileutis | Company | [site](http://mileutis.com/) | [ ] | [ ] |
| `minoryx-therapeutics` | Minoryx Therapeutics | Company | [site](http://www.minoryx.com/) | [ ] | [ ] |
| `oncorna` | OncoRNA | Company | [site](https://oncorna.eu/) | [ ] | [ ] |
| `questa-bio` | Questa Bio | Company | [site](https://questbio.org/) | [ ] | [ ] |
| `railroad-therapeutics` | Railroad Therapeutics | Company | [site](https://www.linkedin.com/company/railroad-therapeutics/about/) | [ ] | [ ] |
| `sagitta-biotech` | Sagitta Biotech | Company | [site](https://sagittabiotech.com/) | [ ] | [ ] |
| `santero-therapeutics` | Santero Therapeutics | Company | [site](https://www.santero.be/) | [ ] | [ ] |
| `silengenics` | Silengenics | Company | [site](https://www.silengenics.com/) | [ ] | [ ] |
| `stellaris-therapeutics` | Stellaris Therapeutics | Company | [site](https://stellaristherapeutics.com/) | [ ] | [ ] |
| `t-knife` | T-knife | Company | [site](http://>%20VISIT%20THEIR%20WEBSITE) | [ ] | [ ] |
| `texere-biotech` | TEXERE Biotech | Company | [site](https://texere.be/fr/) | [ ] | [ ] |
| `usil-therapeutics` | USIL Therapeutics | Company | [site](https://www.usil-therapeutics.com/) | [ ] | [ ] |
| `xomex-bio` | Xomex Bio | Company | [site](https://conveyxo.com/xomexbio/) | [ ] | [ ] |

### Engineering & facilities (6)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `barre` | Barré | Service provider | [site](https://www.barre.eu/) | [ ] | [ ] |
| `ekium` | Ekium | Service provider | [site](https://www.ekium.eu/) | [ ] | [ ] |
| `equans` | Equans | Service provider | [site](https://www.equans.be/) | [ ] | [ ] |
| `igretec` | IGRETEC | Public/Non-profit organisation | [site](http://www.igretec.com/) | [ ] | [ ] |
| `laporte-euro` | Laporte Euro | Service provider | — | [ ] | [ ] |
| `potteau` | Potteau | Service provider | — | [ ] | [ ] |

### Finance & Grants (5)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `altesia` | Altesia | Service provider | [site](https://www.altesia.be) | [ ] | [ ] |
| `dups` | Dups | Service provider | — | [ ] | [ ] |
| `kpmg` | KPMG | Service provider | [site](https://kpmg.com/be/en/home.html) | [ ] | [ ] |
| `mac-jb` | MAC&JB | Service provider | — | [ ] | [ ] |
| `moore-belgium` | MOORE Belgium | Service provider | [site](https://www.moore.be/en/services/grants-incentives) | [ ] | [ ] |

### Go-to-market & Communication (2)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `biopharmark` | Biopharmark | Service provider | [site](https://biopharmark.com/) | [ ] | [ ] |
| `maia-consulting` | Maia Consulting | Service provider | [site](https://maiaconsulting.be/) | [ ] | [ ] |

### HR, Talent & Skills development (9)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `aptaskil` | Aptaskil | Training center | [site](http://www.aptaskil.be/) | [ ] | [ ] |
| `careforce-one` | CareForce One | Service provider | [site](http://www.careforceone.be/) | [ ] | [ ] |
| `centre-de-competence-forem-cepegra` | Centre de Compétence Forem - Cepegra | Training center | [site](https://www.formation-cepegra.be/) | [ ] | [ ] |
| `eu-biotech-campus` | EU Biotech Campus | Training center | [site](https://biotechcampus.eu/) | [ ] | [ ] |
| `nuwhi` | Nuwhï | Service provider | — | [ ] | [ ] |
| `schutz-partners` | SCHÜTZ & PARTNERS | Service provider | [site](https://schutzandpartners.com/#welcome) | [ ] | [ ] |
| `select-hr` | Select HR | Service provider | [site](https://www.selecthr.be/en-GB) | [ ] | [ ] |
| `talentsquare` | Talentsquare | Service provider | [site](https://www.talentsquare.com/) | [ ] | [ ] |
| `technofutur-tic` | Technofutur TIC | Service provider | [site](https://technofuturtic.be/) | [ ] | [ ] |

### Imaging (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `ire-ire-elit` | Ire - Ire ELiT | Company | [site](https://www.ire.eu/) | [ ] | [ ] |

### Insurance (2)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `marsh` | Marsh | Service provider | [site](http://www.marsh.com/) | [ ] | [ ] |
| `van-ingelgem-fils` | Van Ingelgem & Fils | Service provider | [site](https://www.van-ingelgem.be/) | [ ] | [ ] |

### IP & Data protection (2)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `awa` | AWA | Service provider | [site](https://www.awa.com/) | [ ] | [ ] |
| `gevers` | GEVERS | Service provider | [site](http://www.gevers.eu/) | [ ] | [ ] |

### IT, Data  & Cybersecurity (4)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `az-tecnology` | AZ Tecnology | Service provider | — | [ ] | [ ] |
| `cortys` | Cortys | Service provider | — | [ ] | [ ] |
| `dynapps` | Dynapps | Service provider | [site](https://www.dynapps.be/fr?ref=eu-redirect) | [ ] | [ ] |
| `redsystem` | REDSYSTEM | Service provider | [site](https://redsystem.io/) | [ ] | [ ] |

### Laboratory Equipment & Smart Lab Technologies (3)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `analis` | Analis | Service provider | [site](http://www.analis.com) | [ ] | [ ] |
| `greiner-bio-one` | Greiner Bio-One | Service provider | — | [ ] | [ ] |
| `mirrhia` | MIRRHIA | Service provider | [site](https://mirrhia.com/fr/) | [ ] | [ ] |

### Legal (5)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `bossard-associes` | Bossard + Associés | Service provider | [site](https://www.bossard.law/) | [ ] | [ ] |
| `deloitte-legal` | Deloitte Legal | Service provider | [site](https://www.deloittelegal.be/lg/en.html) | [ ] | [ ] |
| `fieldfisher` | Fieldfisher | Service provider | [site](https://www.fieldfisher.com/en-be/locations/belgium) | [ ] | [ ] |
| `harvest-law-firm` | HARVEST LAW FIRM | Service provider | [site](https://www.harvest-legal.be/en/) | [ ] | [ ] |
| `osborne-clarke` | Osborne Clarke | Service provider | [site](http://www.osborneclarke.com/) | [ ] | [ ] |

### Medical Devices (10)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `emma-electronics-mechanics-manufacturing-assembly` | EMMA - Electronics Mechanics Manufacturing Assembly | Company | [site](https://emma-belgium.com/fr/accueil/) | [ ] | [ ] |
| `endo-tools-therapeutics` | Endo Tools Therapeutics | Company | [site](http://www.endotools.be/%20) | [ ] | [ ] |
| `exo-harvest` | Exo-Harvest | Company | [site](https://www.exo-harvest.com/) | [ ] | [ ] |
| `ipratech` | Ipratech | Company | [site](http://www.ipratech.be/%20) | [ ] | [ ] |
| `lys-medical` | Lys Medical | Company | [site](https://lysmedical.com/) | [ ] | [ ] |
| `pulso-technology` | Pulso Technology | Company | [site](https://www.pulsotechnology.com/) | [ ] | [ ] |
| `secoya-technologies` | Secoya Technologies | Company | [site](http://www.secoya-tech.com/) | [ ] | [ ] |
| `slow-surg` | Slow Surg | Company | — | [ ] | [ ] |
| `spentys` | Spentys | Company | [site](https://www.spentys.com/) | [ ] | [ ] |
| `sterigenics` | Sterigenics | Company | [site](https://sterigenics.com/) | [ ] | [ ] |

### Pharma (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `brenus-pharma` | Brenus Pharma | Company | [site](https://brenus-pharma.com/) | [ ] | [ ] |

### Production (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `agricells` | Agricells | Company | [site](https://www.agricells.com) | [ ] | [ ] |

### R&D (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `institut-de-biologie-et-de-medecine-moleculaires-ibmm` | Institut de Biologie et de Médecine Moléculaires (IBMM) | Research Center | [site](https://sciences.ulb.be/le-departement-de-biologie-moleculaire/la-recherche-au-departement-de-biologie-moleculaire) | [ ] | [ ] |

### Software (iQMS,EBR,...) (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `innatify` | Innatify | Company | [site](https://www.innatify.com/) | [ ] | [ ] |

### Strategy, Quality & Process consulting (5)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `agidens` | Agidens | Service provider | [site](http://www.agidens.com/) | [ ] | [ ] |
| `avertim` | Avertim | Service provider | [site](http://www.avertim.com/) | [ ] | [ ] |
| `bio-research-ai` | Bio-research.ai | Service provider | [site](https://bio-research.ai) | [ ] | [ ] |
| `inits` | Inits | Service provider | [site](https://inits.fr/) | [ ] | [ ] |
| `sirris` | Sirris | Service provider | [site](https://www.sirris.be/fr) | [ ] | [ ] |

### Technology Provider (1)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `conveyxo` | ConvEyXO | Company | [site](https://conveyxo.com/%20) | [ ] | [ ] |

### (non classe) (15)

| slug | entreprise | type | site | carr. | scraper |
|---|---|---|---|---|---|
| `biopole-ulb-charleroi-buc` | Biopole ULB Charleroi (BUC) | University | [site](https://www.ulb.be/fr/l-ulb-a-charleroi) | [ ] | [ ] |
| `centre-hospitalier-universitaire-ambroise-pare` | Centre Hospitalier universitaire Ambroise Paré | Hospital | [site](https://www.hap.be/Public/index.php) | [ ] | [ ] |
| `cetic` | CETIC | Public/Non-profit organisation | [site](https://www.cetic.be) | [ ] | [ ] |
| `helha-haute-ecole-louvain-en-hainaut` | HELHa - Haute École Louvain en Hainaut | College | [site](https://www.helha.be/implantation/helha-gosselies/) | [ ] | [ ] |
| `hub` | HUB | Hospital | — | [ ] | [ ] |
| `humani-chu-de-charleroi-chimay` | HUmani CHU de Charleroi-Chimay | Hospital | [site](https://www.humani.be/humani/projets-ia/) | [ ] | [ ] |
| `immunofusion` | Immunofusion | Company | [site](https://immunofusion.com/) | [ ] | [ ] |
| `institut-d-immunologie-medicale-imi` | Institut d'immunologie médicale (IMI) | — | [site](https://u-cri.ulb.be/index.php?action=affiliations) | [ ] | [ ] |
| `kokuma` | KOKUMA | Company | [site](https://www.kokuma.tech/) | [ ] | [ ] |
| `maison-mieux-etre` | Maison Mieux-Être | Foundation | [site](https://maisonmieuxetre.be/) | [ ] | [ ] |
| `syngulon` | Syngulon | Company | [site](https://syngulon.com/) | [ ] | [ ] |
| `u-charleroi` | U Charleroi | University | [site](https://campusucharleroi.be/) | [ ] | [ ] |
| `ulb-universite-libre-de-bruxelles` | ULB - Université libre de Bruxelles | University | [site](http://www.ulb.be/) | [ ] | [ ] |
| `umons` | UMONS | University | [site](https://web.umons.ac.be/fr/) | [ ] | [ ] |
| `viridaxis` | Viridaxis | Company | [site](http://www.viridaxis.com/) | [ ] | [ ] |

## Ecartees — doublons

Deja dans le repertoire, l'import ne les recree pas.

| fiche BioPark | deja en base sous |
|---|---|
| 2 Bridge | 2 Bridge |
| Agence du Numérique | Agence du Numérique |
| BioWin | BioWin |
| Calysta | Calysta |
| Cap4HR | Cap4HR |
| Catalent | Catalent |
| Forem | Le Forem |
| Icosa Europe | ICOSA EUROPE |
| Ignity | Ignity |
| InhaTarget Therapeutics | InhaTarget Therapeutics |
| Jansen Cleanrooms & Labs | Jansen Cleanrooms & Labs |
| My engineering | My Engineering SRL |
| Ooho | Ooho bv |
| PwC Belgium | PwC Belgium |
| QBD Group | QbD Group |
| Quantoom Biosciences | Quantoom Biosciences |
| Sales Attitude | Sales Attitude |
| Strand | Strand |
| Thermo Fisher Scientific | Thermo Fisher Scientific – Henogen |
| Wallonie Entreprendre Life Sciences | Wallonie Entreprendre |

La fiche BioPark de **Thermo Fisher Scientific** donne l'adresse precise du
site de Charleroi (16 rue Clement Ader, 6041) — a reporter sur la ligne
`thermo-fisher-scientific-henogen` si le point sur la carte est approximatif.

## Trous connus

Manques de la source, pas de l'import : la fiche BioPark elle-meme est vide.

- **17 sans site web**, donc sans point de depart pour un scraper :
  3D Fibroscreen, AI4Nursing, AZ Tecnology, Ajimex, Allyfe, Cancer State Therapeutics, Cortys, Dups, Greiner Bio-One, HUB, Laporte Euro, MAC&JB, Neuvasq, Nuwhï, Potteau, Sambrinvest, Slow Surg.
- **12 sans coordonnees** (aucune adresse sur la fiche), absentes
  de la carte tant qu'une adresse n'est pas saisie a la main :
  AbolerIS Pharma, Belfius Namur-Hainaut Sud, Bio-research.ai, Brenus Pharma, CCI France Belgique, Centre de Compétence Forem - Cepegra, Deloitte Legal, Innatify, Laporte Euro, Neuvasq, SCHÜTZ & PARTNERS, Syngulon.
- Le telephone de `REDSYSTEM` est recopie tel quel de la source, ou il est
  malforme (`+32 (0470 47 51 07`).
