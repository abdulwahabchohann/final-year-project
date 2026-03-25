"""
Model Training Module for Sentiment Analysis
Fine-tune emotion detection model on book-specific data
"""

import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
import numpy as np
from sklearn.model_selection import train_test_split
from typing import List, Dict
import os


class BookEmotionDataset(Dataset):
    """Dataset for book emotion classification"""
    
    def __init__(self, texts: List[str], labels: List[Dict], tokenizer, max_length: int = 512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Define emotion categories
        self.emotion_names = [
            'joy', 'sadness', 'anger', 'fear', 'surprise',
            'love', 'optimism', 'calm', 'excitement'
        ]
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label_dict = self.labels[idx]
        
        # Tokenize text
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        # Create multi-label vector
        label_vector = torch.zeros(len(self.emotion_names))
        for i, emotion in enumerate(self.emotion_names):
            label_vector[i] = label_dict.get(emotion, 0.0)
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': label_vector
        }


class SentimentModelTrainer:
    """Train and fine-tune sentiment analysis models"""
    
    def __init__(self, base_model: str = "distilbert-base-uncased"):
        """
        Initialize trainer
        
        Args:
            base_model: HuggingFace base model to fine-tune
        """
        self.base_model = base_model
        self.tokenizer = None
        self.model = None
        self.emotion_names = [
            'joy', 'sadness', 'anger', 'fear', 'surprise',
            'love', 'optimism', 'calm', 'excitement'
        ]
    
    def prepare_training_data(self, dataset_path: str, sample_size: int = None):
        """
        Prepare training data from book dataset
        
        Args:
            dataset_path: Path to books JSON file
            sample_size: If specified, use only this many books for training
            
        Returns:
            Tuple of (train_texts, train_labels, val_texts, val_labels)
        """
        print(f"Loading dataset from {dataset_path}...")
        
        with open(dataset_path, 'r', encoding='utf-8') as f:
            books = json.load(f)
        
        if sample_size:
            books = books[:sample_size]
        
        print(f"Preparing {len(books)} books for training...")
        
        texts = []
        labels = []
        
        # For training, we'll use book descriptions as inputs
        # and generate synthetic emotion labels based on keywords
        for book in books:
            description = book.get('description', '')
            if not description or len(description) < 50:
                continue
            
            texts.append(description)
            
            # Use existing mood_scores if available, otherwise generate synthetic
            mood_scores = book.get('mood_scores', {})
            if isinstance(mood_scores, str):
                try:
                    mood_scores = json.loads(mood_scores)
                except:
                    mood_scores = {}
            
            # Create label dict with all emotion categories
            label_dict = {emotion: 0.0 for emotion in self.emotion_names}
            
            # If we have existing scores, use them
            for emotion in self.emotion_names:
                if emotion in mood_scores:
                    label_dict[emotion] = float(mood_scores[emotion])
            
            # If no existing scores, generate based on keywords (weak supervision)
            if sum(label_dict.values()) == 0:
                label_dict = self._generate_weak_labels(description)
            
            labels.append(label_dict)
        
        print(f"Prepared {len(texts)} training samples")
        
        # Split into train/validation
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
        
        print(f"Train: {len(train_texts)}, Validation: {len(val_texts)}")
        
        return train_texts, train_labels, val_texts, val_labels
    
    def _generate_weak_labels(self, text: str) -> Dict[str, float]:
        """Generate weak labels based on keyword matching"""
        text_lower = text.lower()
        labels = {emotion: 0.0 for emotion in self.emotion_names}
        
        # Keyword mappings
        keywords = {
            'joy': ['happy', 'joy', 'delightful', 'wonderful', 'cheerful', 'pleased'],
            'sadness': ['sad', 'depressing', 'melancholy', 'tragic', 'sorrow'],
            'anger': ['angry', 'rage', 'fury', 'hostile', 'violent'],
            'fear': ['fear', 'scary', 'terror', 'horror', 'frightening'],
            'surprise': ['surprise', 'unexpected', 'shocking', 'astonishing'],
            'love': ['love', 'romance', 'romantic', 'passion', 'affection'],
            'optimism': ['hope', 'optimis', 'inspiring', 'uplifting', 'positive'],
            'calm': ['calm', 'peaceful', 'serene', 'tranquil', 'relaxing'],
            'excitement': ['exciting', 'thrilling', 'exhilarating', 'adventure']
        }
        
        for emotion, words in keywords.items():
            count = sum(1 for word in words if word in text_lower)
            labels[emotion] = min(count * 0.3, 1.0)  # Cap at 1.0
        
        # Normalize
        total = sum(labels.values())
        if total > 0:
            labels = {k: v / total for k, v in labels.items()}
        
        return labels
    
    def train(
        self,
        train_texts: List[str],
        train_labels: List[Dict],
        val_texts: List[str],
        val_labels: List[Dict],
        output_dir: str = "./trained_sentiment_model",
        num_epochs: int = 3,
        batch_size: int = 8
    ):
        """
        Train the sentiment model
        
        Args:
            train_texts: Training texts
            train_labels: Training labels
            val_texts: Validation texts
            val_labels: Validation labels
            output_dir: Directory to save trained model
            num_epochs: Number of training epochs
            batch_size: Training batch size
        """
        print(f"\nInitializing model: {self.base_model}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        
        # Load model for multi-label classification
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.base_model,
            num_labels=len(self.emotion_names),
            problem_type="multi_label_classification"
        )
        
        # Create datasets
        train_dataset = BookEmotionDataset(train_texts, train_labels, self.tokenizer)
        val_dataset = BookEmotionDataset(val_texts, val_labels, self.tokenizer)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=f'{output_dir}/logs',
            logging_steps=100,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
        )
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
        )
        
        # Train
        print("\nStarting training...")
        trainer.train()
        
        # Save final model
        print(f"\nSaving model to {output_dir}")
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        print("✓ Training complete!")
        
        return trainer


def train_sentiment_model(
    dataset_path: str = "books_dataset_5000.json",
    output_dir: str = "./trained_book_sentiment_model",
    sample_size: int = 1000,
    epochs: int = 3
):
    """
    Main function to train sentiment model
    
    Args:
        dataset_path: Path to books dataset
        output_dir: Where to save trained model
        sample_size: Number of books to use for training (None = all)
        epochs: Number of training epochs
    """
    print("="*80)
    print("SENTIMENT MODEL TRAINING")
    print("="*80)
    
    # Check if transformers is available
    try:
        import transformers
    except ImportError:
        print("\n❌ Error: transformers not installed!")
        print("Install with: pip install transformers torch")
        return
    
    # Initialize trainer
    trainer = SentimentModelTrainer(base_model="distilbert-base-uncased")
    
    # Prepare data
    train_texts, train_labels, val_texts, val_labels = trainer.prepare_training_data(
        dataset_path,
        sample_size=sample_size
    )
    
    # Train
    trained_model = trainer.train(
        train_texts,
        train_labels,
        val_texts,
        val_labels,
        output_dir=output_dir,
        num_epochs=epochs,
        batch_size=8
    )
    
    print(f"\n{'='*80}")
    print("TRAINING SUMMARY")
    print(f"{'='*80}")
    print(f"✓ Model saved to: {output_dir}")
    print(f"✓ Training samples: {len(train_texts)}")
    print(f"✓ Validation samples: {len(val_texts)}")
    print(f"✓ Epochs: {epochs}")
    print("\nTo use this model, update sentiment_analyzer.py:")
    print(f"  EmotionAnalyzer(model_name='{output_dir}')")


if __name__ == "__main__":
    import sys
    
    print("\nBook Sentiment Model Training")
    print("="*80)
    
    # Check if dataset exists
    dataset_path = "books_dataset_5000.json"
    if not os.path.exists(dataset_path):
        print(f"\n❌ Error: Dataset not found at {dataset_path}")
        print("Please run export_books_dataset.py first to generate the dataset.")
        sys.exit(1)
    
    # Parse command line arguments
    sample_size = 1000  # Use subset for faster training
    epochs = 3
    
    if len(sys.argv) > 1:
        sample_size = int(sys.argv[1])
    if len(sys.argv) > 2:
        epochs = int(sys.argv[2])
    
    print(f"\nConfiguration:")
    print(f"  Dataset: {dataset_path}")
    print(f"  Sample size: {sample_size} books")
    print(f"  Epochs: {epochs}")
    print(f"  Output: ./trained_book_sentiment_model")
    
    response = input("\nProceed with training? (y/n): ")
    if response.lower() == 'y':
        train_sentiment_model(
            dataset_path=dataset_path,
            sample_size=sample_size,
            epochs=epochs
        )
    else:
        print("Training cancelled.")

