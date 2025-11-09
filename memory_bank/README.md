# Memory Bank - RAG Corpus

This directory contains the corpus for the Strategic Type Agent's RAG (Retrieval-Augmented Generation) system.

## Purpose

The Strategic Type Agent queries this memory bank to apply proven content strategies from "The Tech Audience Accelerator" newsletter corpus.

## File Format

- Files should be in `.txt` format
- Each file represents a newsletter or content piece
- Content will be ingested into a vector store for semantic search

## Setup

During Phase 7 (Memory Bank Content), this directory will be populated with:
- Sample newsletter text files
- Content strategy examples
- Structural templates

## Usage

The RAG system (implemented in `core/rag_setup.py`) will:
1. Ingest all `.txt` files from this directory
2. Create vector embeddings
3. Enable semantic search queries from agents

## Note

This directory is currently empty and will be populated during development.
