# CVEngine (Skill-Matcher)
An intelligent CV processing and employee matching system that analyzes resumes, extracts skills, and ranks employees based on semantic similarity to required competencies.

## Overview
CVEngine processes employee CVs, transforms them into structured objects, embedded with te vectorialization of the text, and performs intelligent matching when specific skills are requested. The system uses semantic analysis to rank the best-suited employees for given skill requirements.

## Features
- CV parsing and structured data extraction
- Semantic skill matching and employee ranking
- Multiple matching algorithms (Semantic, Logic, Ontologic)
- Interactive web interface powered by Streamlit
- Excel export functionality
- Real-time feedback and logging system

## Installation
Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/CVEngine.git
cd CVEngine
pip install -r requirements.txt
```

## Usage
Quick Start
Run the main application:

```bash
streamlit run Welcome.py
```

Example: Finding Employees by Skills

```python
from components.keywords import Keywords
from components.jaeger import Jaeger
from components.cvs import CVS

# Initialize the CVS collector
cvs = CVS()
cvs.load_pkl() # Load the database

# Initialize the engine
jaeger = Jeager(cvs=cvs)

# Define required skills
required_skills = ["Python", "Machine Learning", "Data Analysis"]
keywords = Keywords(list(key_names), list(weights))

# Get ranked employees
results = jaeger.export_results(keywords=keywords, show=True, runtype='semantic')

# Display results as table
print(results.to_dataframe())
```

## Project Structure
```
CVEngine
├─ README.md
├─ Welcome.py               # Main Streamlit Interface
├─ api_cv.py                # API Endopoints
├─ client.py
├─ components
│  ├─ config.py
│  ├─ constants.py          
│  ├─ cv.py                 # CV Object model
│  ├─ cvs.py                # CV collection management
│  ├─ feedback.py           # Feedback system management
│  ├─ jaeger.py             # Matching Engine Core 
│  ├─ keywords.py           # Keywords Object model
│  ├─ llm.py                # LLM model integration
│  ├─ logger.py             # Custom logging system
│  ├─ matrix.py             
│  ├─ person.py             # Additional inforation model
│  ├─ sql_connector.py
│  └─ summarizer.py         # Summarization system
├─ create_archive.py
├─ main.py
├─ pages
│  ├─ 1_Semantic.py         # Streamlit Semantic Search 
│  ├─ 2_Logic.py            # Streamlit Logic Search 
│  ├─ 3_Ontologic.py        # Streamlit Onotologic Search
│  ├─ 4_Matrix.py           # Streamlit Matrix Search 
│  └─ 5_Summary.py          # Streamlit Summarization 
├─ requirements.txt
└─ test_person.py
```

### Requirements
- Python 3.11+
- See requirements.txt for full dependency list

## Matching Algorithms
The system supports multiple matching approaches:

- *Semantic*: Uses semantic similarity for skill matching

- *Logic*: Rule-based matching logic

- *Ontologic*: Ontology-driven skill relationships

- *Matrix*: Similarity matrix computation

### Semantic Search DeepDive
The *Semantic Matching Algorithm* is the core of the CVEngine's Intelligence. It process the strucutre of the Data and performs the similarity in orther to extract the final ranking of the best-suited employee.

#### Vector Embedding Architecture
Instead of using traditional vector databases (Milvus, Chroma, Pinecone, etc..), CVEngine employs an embedded vectorization approach where each CV object contains its own vector representations. This design choice offers several advantages:
- **Portability**: CV objects are self-contained with their embeddings
- **Flexibility**: No dependency on external vector database infrastructure
- **Transparency**: Direct control over similarity computation
- **Efficiency**: Reduced latency by eliminating database queries
- **Compliance**: All the Data and Metadata are not shared across cloud services

Here an example of the CV object definition:

```python
class CVperson:
    def __init__(self, ..., fragments: list[list[float]] = None):
        ...
        self.bert_model = BertModel.GTE_LARGE
        embedding_model = SentenceTransformer(self.bert_model.value)
        if fragments is None:
            self.fragments = self.embed(embedding_model, self.split(text=body, model=self.bert_model.value))
        else:
            self.fragments = fragments

    @staticmethod
    def split(text: str, model: str) -> list[str]:
        """
        Split the text into fragments based on the maximum token length of the model (512 token for GTE Large model)
        ...
        """
        tokenizer = AutoTokenizer.from_pretrained(model)
        text_splitter = TokenTextSplitter.from_huggingface_tokenizer(
            tokenizer, chunk_size=128, chunk_overlap=50
        )
        logger.debug(f"Text split into {len(text_splitter.split_text(text))} fragments")
        return text_splitter.split_text(text)

    @staticmethod
    def embed(model, docs: list[str]) -> list[list[float]]:
        """
        Embed the list of fragments using the Sentence Transformer model
        ...
        """
        embedded_docs = []
        for doc in docs:
            embedded_docs.append(model.encode(doc))
        logger.debug("CV embedding completed")
        return [arr.tolist() for arr in embedded_docs]
```

How It Works:

#### 1. CV Chunking and Vectorization
When a employee information is processsed its extract all the meaningful information: the CV it's divided into meaningful chunks (skills, experiences, education); all the other information are embedded in the class attributes and in the Person object. 
Each chunk of the CV is transformed into a high-dimensional vector using specific *embedding models*:

```text
Original CV Document
┌─────────────────────────────────────────┐
│ John Doe                                │
│ Skills: Python, SATA, Autoclave         │
│ Experience: 5 years as Data Scientist   │
│ Education: MSc Computer Science         │
│ Projects: Built recommendation system   │
└─────────────────────────────────────────┘
                    │
                    ▼
            Text Extraction
                    │
                    ▼
              Chunking Process
                    │
        ┌───────────┼───────────┬──────────┐
        ▼           ▼           ▼          ▼
    ┌───────┐  ┌────────┐  ┌─────────┐  ┌─────────┐
    │Chunk 1│  │Chunk 2 │  │Chunk 3  │  │Chunk 4  │
    │Skills │  │Work    │  │Education│  │Projects │
    └───────┘  └────────┘  └─────────┘  └─────────┘
        │          │           │            │
        ▼          ▼           ▼            ▼
    [0.23,    [0.45,      [0.12,       [0.89,
    0.67,     0.21,       0.78,        0.34,
    0.91,     0.88,       0.45,        0.56,
    ...]      ...]        ...]         ...]
    
    512-dim    512-dim     512-dim      512-dim
    vector     vector      vector       vector
```

Of course it can happen that different CVs can have different lengths, for this reason the system is built to deal with different length of vectorization:

```text
CV Object Structure in Memory:

Employee A (Junior)                Employee B (Senior)
┌─────────────────────┐           ┌─────────────────────┐
│ CV Object           │           │ CV Object           │
│ ├─ Metadata         │           │ ├─ Metadata         │
│ └─ Chunks: 3        │           │ └─ Chunks: 7        │
│    ├─ [vec_1]       │           │    ├─ [vec_1]       │
│    ├─ [vec_2]       │           │    ├─ [vec_2]       │
│    └─ [vec_3]       │           │    ├─ [vec_3]       │
└─────────────────────┘           │    ├─ [vec_4]       │
                                  │    ├─ [vec_5]       │
                                  │    ├─ [vec_6]       │
                                  │    └─ [vec_7]       │
                                  └─────────────────────┘

Employee C (Mid-level)
┌─────────────────────┐
│ CV Object           │
│ ├─ Metadata         │
│ └─ Chunks: 5        │
│    ├─ [vec_1]       │
│    ├─ [vec_2]       │
│    ├─ [vec_3]       │
│    ├─ [vec_4]       │
│    └─ [vec_5]       │
└─────────────────────┘
```

#### 2. Skills Embedding
Since cosine similarity operates on vector comparisons, the skills must first be converted into embedded vectors. This is done in a similar way as for the CV object.

```python
class Keywords:
    """
    A class to represent a collection of keywords and their weights for text matching.
    ...                     
    """
    def __init__(self, words: list[str], weights: list[float]) -> None:
        self.bert_model = BertModel.GTE_LARGE
        embedding_model = SentenceTransformer(self.bert_model.value)
        self.embedded_words = {word: {'embedding': embedding_model.encode(word).tolist(),
                                      'weight': weight} for word, weight in zip(words, weights)}
        self.weights = weights
```

#### 3. Cosine Similarity Computation
When matching skills, the system computes the cosine similarity between the embedded vector of each query skill and every embedded chunk within a CV:

$$
\text{similarity}(A, B) = \frac{A \cdot B}{\|A\| \, \|B\|}
$$

This metric evaluates the angle between two vectors in the semantic space: values closer to 1 indicate strong similarity, while values near 0 indicate weak or no relation.

For each CV, the system aggregates the individual similarity scores of all matched chunks by computing their average. This produces a single, normalized relevance score representing how well the CV matches the queried skill set. In other words:

$$
\text{CV Score} = \frac{1}{n} \sum_{i=1}^{n} \text{similarity}(skill, chunk_i)
$$

#### 4. Ranking and Aggregation

For each employee, the system:
- Calculates similarity scores for all relevant CV chunks
```python
class CVperson:
    ...
    def match_words(self, words: list[list[float]]) -> list[float]:
        """
        Compute the similarity of each words with all the fragments of the CV and return a list of similarity values
        ...
        """
        similarities = cosine_similarity(words, self.fragments)
        return similarities.max(axis=1)
```
- Aggregates scores to produce an overall match rating
- Ranks employees by their final similarity scores

```text
User Query: "Machine Learning Engineer"
         │
         ▼
    Vectorize Query
    [0.34, 0.12, 0.89, ...]
         │
         ▼
    ┌────┴─────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
Employee A  Employee B  Employee C  Employee D
  (3 chunks)  (7 chunks)  (5 chunks)  (4 chunks)
    │          │          │          │
    ▼          ▼          ▼          ▼
Compute cosine similarity with ALL chunks
    │          │          │          │
    ▼          ▼          ▼          ▼
  Mean:       Mean:     Mean:       Mean:
    0.73      0.91      0.85        0.68
    │          │          │          │
    └──────────┴──────────┴──────────┘
                 │
                 ▼
         Ranked Results:
         1. Employee B (0.91)
         2. Employee C (0.85)
         3. Employee A (0.73)
         4. Employee D (0.68)
```

## Future Improvements
Contributions are welcome! Please feel free to submit a Pull Request.

## License
[To be determined]
