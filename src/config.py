import streamlit as st
DATA_PATH = "V:\\STRI\\NOBACKUP\\stri_calculation_data\\stri_regdb_2024.dta"
DIGITAL_STRI_PATH = "V:\\STRI\\NOBACKUP\\stri_calculation_data\\dstri_regdb_2024.dta"
NEW_DATA_PATH = "C:\\Users\\Joksimovic_j\\Documents\\stri-chatbot\\stri_oecdstat_2014_2024_copy.xlsx"
OPENAI_API_KEY = st.secrets["openai_api_key"]
FEEDBACK_FILE = "./feedback.jsonl"
SECTOR_CODES = {
    "CS": "COMPUTER SERVICES",
    "TC": "TELECOMMUNICATION",
    "ASBRD": "BROADCASTING",
    "ASMOT": "MOTION PICTURES",
    "ASSOU": "SOUND RECORDING",
    "TRAIR": "AIR TRANSPORT",
    "TRMAR": "MARITIME TRANSPORT",
    "TRROF": "ROAD FREIGHT TRANSPORT",
    "TRRAI": "RAIL FREIGHT TRANSPORT",
    "CR": "COURIER SERVICES",
    "DS": "DISTRIBUTION SERVICES",
    "LSCAR": "LOGISTICS CARGO-HANDLING",
    "LSSTG": "LOGISTICS STORAGE AND WAREHOUSE",
    "LSFGT": "LOGISTICS FREIGHT FORWARDING",
    "LSCUS": "LOGISTICS CUSTOMS BROKERAGE",
    "PSLEG": "LEGAL SERVICES",
    "PSACC": "ACCOUNTING SERVICES",
    "FSBNK": "COMMERCIAL BANKING",
    "FSINS": "INSURANCE",
    "CO": "CONSTRUCTION",
    "PSARC": "ARCHITECTURE SERVICES",
    "PSENG": "ENGINEERING SERVICES"
}

OECD_AVERAGE = 0.22

SECTORS_AVERAGE = {
    "PSACC": 0.322659730911255,      # Accounting services
    "LSCAR": 0.233585208654404,      # Cargo-handling
    "FSINS": 0.208545953035355,      # Insurance
    "TRRAI": 0.314981997013092,      # Rail freight transport
    "CO":    0.220207899808884,      # Construction
    "TRAIR": 0.399120539426804,      # Air transport
    "PSARC": 0.241186633706093,      # Architecture services
    "PSENG": 0.21505418419838,       # Engineering services
    "PSLEG": 0.343156576156616,      # Legal services
    "ASBRD": 0.304061651229858,      # Broadcasting
    "TC":    0.232308134436607,      # Telecommunication
    "CS":    0.198586478829384,      # Computer services
    "TRMAR": 0.2597716152668,        # Maritime transport
    "FSBNK": 0.225348696112633,      # Commercial banking
    "TRROF": 0.213518902659416,      # Road freight transport
    "CR":    0.252106219530106,      # Courier services
    "LSFGT": 0.203660130500793,      # Freight-forwarding
    "LSSTG": 0.227044105529785,      # Storage and warehouse
    "DS":    0.193911269307137,      # Distribution services
    "ASSOU": 0.192660689353943,      # Sound recording
    "LSCUS": 0.222166672348976       # Customs brokerage
}


SECTOR_DESCRIPTIONS = {
    "CS": "Computer services are defined as computer programming, consultancy and related activities and information service activities (ISIC Rev 4 code 62 and 63). Major exporters are the European Union, India and the United States. The importance of computer services has grown significantly in the past decades driving the development of a data-driven global economy. Computer services are mainly traded business to business. Supply of services across borders are prominent in this sector, especially as the quality of the communication infrastructure improves worldwide. Nonetheless, cross-border supplies are often complemented with technical expertise for installation, use and maintenance requiring travel for computer engineers and other technical experts.",
    "CO": "The STRI covers construction of buildings (residential and non-residential) as well as construction work for civil engineering (ISIC Rev 4, codes 41-43). Construction services have historically played an important role in the functioning of economies, providing the infrastructure for other industries. These services account for a significant share of gross domestic product (GDP) and employment in most countries. Public works, such as roads and public buildings, account for about half of the market for construction services. Therefore, the STRI for construction services covers detailed information on public procurement procedures.",
    "PSleg": "Legal services (ISIC Rev 4, code 691) cover advisory and representation services in domestic and international law, and where relevant measures are entered separately for each of them. International law includes advisory services in home country law, third country law, international law, as well as a right to appear in international commercial arbitration. Domestic law extends to advising and representing clients before a court or judicial body in the law of the host country.",
    "PSacc": "The STRI covers accounting, auditing and book-keeping services (ISIC Rev 4 code 692). The international market for these services is dominated by a handful of corporations characterised by a high degree of concentration, organised as a network, and generally owned and managed independently with presence in a large number of countries.",
    "PSarc": "The sector covers architectural services and related technical consultancy (ISIC Rev 4, code 71). These services constitute the backbone of the construction sector, with key roles in building design and urban planning. An important feature is the regulatory complementarity between architecture, engineering and construction services. Often, architectural and engineering activities are combined into projects offered by one company, and are sometimes subsumed within the building and construction sector.",
    "PSeng": "The definition of engineering services (ISIC Rev 4, code 71) covers several related activities, such as engineering and integrated engineering services, and engineering related scientific and technical consulting services. Engineering services constitute the backbone of construction and provide essential inputs for the economy.",
    "TC": "The telecommunication sector comprises wired and wireless telecommunications activities (ISIC Rev 4 code 61). Modern telecommunication network are essential as without them global value chains would be impossible. Furthermore, these services are at the core of our information driven society and provide the network over which other services including computer services, audiovisual services, professional services and many more are traded.",
    "DS": "The STRI for the distribution services sector covers general wholesale and retail sales of consumer goods (ISIC Rev 4 codes 46 and 47), though specific regulations of speciality distribution sectors such as pharmaceuticals and motor vehicles are not considered. The STRI in this sector also covers regulations relating to electronic commerce, given the increasing prevalence of multi-channel retail services as a form of distribution services.",
    "ASbrd": "Television and broadcasting include television programming and broadcasting activities (ISIC Rev 4 code 591 and 602). Television services are increasingly bundled with telecommunications services in the marketplace. Telecommunications operators often offer Internet Protocol Television (IPTV) as part of so-called triple play or quadruple play packages (broadband, television and telephone; adding mobile for quadruple play), and in some cases broadcasters have become telecommunications operators. In addition to linear broadcasting, video on demand has become an increasingly important distributor of audio-visual content. Furthermore, there are a host of suppliers offering streaming or downloading on the Internet.",
    "ASmot": "The sector of motion pictures is defined as motion picture, video and television programme production, post-production and distribution activities (ISIC Rev 4, code 591). The sector has benefitted from rapid digitalisation and the increased technological developments that facilitate the streaming of media content over the Internet.",
    "ASsou": "Sound recording services cover sound recording and music publishing activities (ISIC Rev 4, code 592). The sector has been subject to rapid digitisation with music streaming becoming an important basis for monetising the migration of physical records to digital platforms.",
    "TRair": "Air transport services are defined as passenger and freight air transport (ISIC Rev 4, code 51), carried domestically or internationally. The STRI for this sector covers commercial establishment only. Air transport services are not only significantly traded in their own right but are an intermediate service for other kinds of trade. Air cargo transport is also a key determinant in meeting demand for time sensitive products, such as perishable goods, and often represents the only viable means of transport to remote, peripheral regions and landlocked countries. Major exporters of air transport services are the European Union and the United States.",
    "TRmar": "Maritime freight transport services cover sea shipping and related port activities (ISIC Rev 4, code 5012). Maritime transport services, as covered by the STRI, refer to seaborne transport of freight and port and auxiliary services necessary to enable maritime transport, such as the access to essential facilities at ports, the provision and use of port services, including marine services, maintenance and repairs services and other activities linked to the ability to organize the ship transport (maritime-related documentation, cargo-handling, etc.). Maritime passenger transport, transport on internal waterways and services necessary to support maritime transport movements (pilotage, towing, tugging, and cargo-handling) are excluded.",
    "TRrai": "Rail transport is provided over a dedicated network where the market structure may take different forms, the two most common ones being: i) vertically integrated rail services firms owning and managing both the infrastructure and the operation of freight services; and ii) vertically separation between the infrastructure management and the operations. No matter the market structure, there are well-established best practice regulations that also take into account competition from other modes of transport, particularly road transport. Transport and courier services are not only extensively traded they are also intermediate services at the core of recent developments in global value chains and just-in-time inventory management, with the related demand for door-to-door services. Reducing unnecessary restrictions and improving productivity in the various sub-sectors can be expected to have significant benefits in downstream industries as well as in the sub-sectors themselves.",
    "TRrof": "Road freight transport is defined as ISIC (rev 4) category 4293 freight transport by road. The STRI for this sector covers commercial establishment only. Cross-border trade is governed by a system of bilateral and plurilateral agreements which provide for permits, quotas and other regulations.",
    "CR": "The sector is defined under ISIC Rev 4 code 53 as postal and courier activities. While digitization has reduced traditional letter mails, e-commerce growth increases the demand for parcels and express deliveries. As the supply chains connect more deeply, timely, precise, and reliable delivery services become critical.",
    "FSbnk": "Commercial banking is defined as comprising deposit-taking, lending and payment services (ISIC Rev 4, code 64). Major exporters of financial services (insurance excluded) are the United States, the United Kingdom and Luxembourg. Commercial banking services are traded business to business, as well as business to consumer for retail banking. Efficient banking services are one of the backbones of dynamic economies; they provide financing for investment and trade across productive activities, underlying all value chains. It should be noted that banking is a heavily regulated sector for the purpose of maintaining the stability and soundness of the financial system. Prudential rules and standards are set by national governments and regulators as well as international financial standard-setting bodies. The STRI does not seek to define the scope or nature of what measures would be considered prudential, but aims to record in an objective and comparable manner the state of legal and regulatory impediments faced by foreign banks.",
    "FSins": "Insurance services (ISIC Rev 4, codes 651 and 652) comprise life insurance, property and casualty insurance, reinsurance and auxiliary services. Private health insurance and private pensions are not covered. Major exporters are the United States, the United Kingdom and Ireland. Efficient insurance services are one of the backbones of dynamic economies, providing firms with risk management tools and channelling savings towards long-term investment. It should be noted that insurance is a heavily regulated sector for the purpose of maintaining the stability and soundness of the financial system. Prudential rules and standards are set by national governments and regulators as well as international financial standard-setting bodies. The STRI does not seek to define the scope or nature of what measures would be considered prudential, but aims to record in an objective and comparable manner the state of legal and regulatory impediments faced by foreign insurers.",
    "LScar": "Logistics services cargo-handling services (ISIC 5224, CPC 741) covers activities such as loading and unloading of goods or passengers’ luggage irrespective of the mode of transport used for transportation, stevedoring and loading and unloading of freight railway cars. Non-core activities cut across several services sectors, particularly transport, distribution and other business services. The core elements of transport and distribution services are already covered in the STRI project. Logistics services play a crucial role in the development of global value chains. They connect production sites as well as manufacturers and consumers by moving goods speedily, reliably and economically. Three recent economic and social trends have influenced the practice of logistics services providers: increasing importance of supply chain management, proliferation of e-commerce and increase of environmental concerns.",
    "LSstg": "Logistics services storage and warehousing services (including customs warehouse services) (ISIC 5210, CPC 742) comprise operation of storage and warehouse facilities for all kind of goods: operation of grain silos, general merchandise warehouses, refrigerated warehouses, storage tanks etc. It also includes the storage of goods in foreign trade zones and blast freezing. Non-core activities cut across several services sectors, particularly transport, distribution and other business services. The core elements of transport and distribution services are already covered in the STRI project. Logistics services play a crucial role in the development of global value chains. They connect production sites as well as manufacturers and consumers by moving goods speedily, reliably and economically. Three recent economic and social trends have influenced the practice of logistics services providers: increasing importance of supply chain management, proliferation of e-commerce and increase of environmental concerns.",
    "LSfgt": "Logistics services freight transport agency services and customs brokerage services (ISIC 5229, CPC 748&749) encompass various activities related to the transportation, storage, handling, and distribution of goods, including advisory services on customs, insurance, and payment matters. These services can be performed using single or multimodal transport methods.",
    "LScus": "Logistics services customs brokerage services (ISIC 5229, CPC 748&749) act as an intermediary for importers and exporters in handling the sequence of customs formalities involved in the customs clearance and importing/importation of goods."
}

STRI_DEFINITION = """
The OECD Services Trade Restrictiveness Index (STRI) is a unique tool that offers an overview of regulatory barriers across 22 major sectors and 51 countries. Updated annually, the STRI also monitors recent regulatory trends, facilitates benchmarking of services policies against global best practices, and enables analysis of the impact of reform options.
"""

KNOWLEDGE_BASE = [SECTOR_DESCRIPTIONS, STRI_DEFINITION]
