"""
Comprehensive Test Suite for Sentiment Analysis Module
"""

import json
import unittest
from sentiment_analyzer import (
    EmotionAnalyzer,
    BookProcessor,
    SentimentScorer,
    ExplainabilityEngine,
    RecommendationEngine
)


class TestEmotionAnalyzer(unittest.TestCase):
    """Test emotion detection functionality"""
    
    @classmethod
    def setUpClass(cls):
        cls.analyzer = EmotionAnalyzer()
    
    def test_emotion_detection_happy_text(self):
        """Test detection of joyful emotions"""
        text = "This is a wonderful, delightful story full of joy and happiness!"
        emotions = self.analyzer.analyze_text(text)
        
        self.assertIsInstance(emotions, dict)
        # Should detect positive emotions
        positive_score = emotions.get('joy', 0) + emotions.get('optimism', 0)
        self.assertGreater(positive_score, 0, "Should detect positive emotions in happy text")
    
    def test_emotion_detection_sad_text(self):
        """Test detection of sad emotions"""
        text = "A tragic and melancholy tale of loss and sorrow"
        emotions = self.analyzer.analyze_text(text)
        
        self.assertIsInstance(emotions, dict)
        # Should have some sadness
        self.assertGreater(emotions.get('sadness', 0) + emotions.get('fear', 0), 0)
    
    def test_empty_text(self):
        """Test handling of empty text"""
        emotions = self.analyzer.analyze_text("")
        self.assertEqual(emotions, {})
        
        emotions = self.analyzer.analyze_text(None)
        self.assertEqual(emotions, {})
    
    def test_multi_emotion_detection(self):
        """Test detection of multiple emotions"""
        text = "A beautiful yet bittersweet story of love, loss, and hope"
        emotions = self.analyzer.analyze_text(text)
        
        # Should detect multiple emotions
        self.assertGreater(len(emotions), 0)
        # Check it returns scores between 0 and 1
        for score in emotions.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


class TestBookProcessor(unittest.TestCase):
    """Test book processing functionality"""
    
    def test_extract_text_full_book(self):
        """Test text extraction from complete book data"""
        book = {
            'title': 'Test Book',
            'author': 'Test Author',
            'description': 'A wonderful story about friendship',
            'reviews': ['Great book!', 'Loved it!']
        }
        
        text = BookProcessor.extract_text(book)
        
        self.assertIn('Test Book', text)
        self.assertIn('friendship', text)
        self.assertIn('Great book', text)
    
    def test_extract_text_minimal_book(self):
        """Test with minimal book data"""
        book = {'title': 'Simple Title'}
        text = BookProcessor.extract_text(book)
        
        self.assertEqual(text, 'Simple Title')
    
    def test_preprocess_text(self):
        """Test text preprocessing"""
        messy_text = "  Multiple   spaces   and\n\nnewlines  "
        clean_text = BookProcessor.preprocess_text(messy_text)
        
        self.assertEqual(clean_text, "Multiple spaces and newlines")


class TestSentimentScorer(unittest.TestCase):
    """Test sentiment scoring functionality"""
    
    @classmethod
    def setUpClass(cls):
        cls.scorer = SentimentScorer()
    
    def test_emotion_similarity_identical(self):
        """Test similarity with identical emotions"""
        emotions1 = {'joy': 0.8, 'love': 0.6}
        emotions2 = {'joy': 0.8, 'love': 0.6}
        
        similarity = self.scorer.calculate_emotion_similarity(emotions1, emotions2)
        
        # Should be very high (close to 1.0)
        self.assertGreater(similarity, 0.95)
    
    def test_emotion_similarity_different(self):
        """Test similarity with opposite emotions"""
        emotions1 = {'joy': 0.9, 'optimism': 0.8}
        emotions2 = {'sadness': 0.9, 'fear': 0.8}
        
        similarity = self.scorer.calculate_emotion_similarity(emotions1, emotions2)
        
        # Should be low
        self.assertLess(similarity, 0.5)
    
    def test_emotion_similarity_empty(self):
        """Test with empty emotion dictionaries"""
        similarity = self.scorer.calculate_emotion_similarity({}, {})
        self.assertEqual(similarity, 0.0)
    
    def test_match_score_range(self):
        """Test that match scores are in valid range"""
        user_emotions = {'joy': 0.5, 'calm': 0.3}
        book_emotions = {'joy': 0.6, 'optimism': 0.4}
        book = {
            'description': 'A calming story about finding peace',
            'genres': ['Fiction']
        }
        
        score = self.scorer.calculate_match_score(
            "feeling happy",
            user_emotions,
            book,
            book_emotions
        )
        
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestExplainabilityEngine(unittest.TestCase):
    """Test explanation generation"""
    
    def test_generate_explanation(self):
        """Test basic explanation generation"""
        book = {
            'title': 'Happy Days',
            'genres': ['Fiction', 'Comedy'],
            'description': 'A story about friendship and overcoming challenges'
        }
        book_emotions = {'joy': 0.8, 'optimism': 0.7}
        user_emotions = {'joy': 0.6, 'calm': 0.4}
        
        explanation = ExplainabilityEngine.generate_explanation(
            book, book_emotions, user_emotions, 0.85
        )
        
        self.assertIsInstance(explanation, str)
        self.assertGreater(len(explanation), 20)
        # Should end with period
        self.assertTrue(explanation.endswith('.'))
    
    def test_complementary_recommendation_explanation(self):
        """Test explanation for mood-improving recommendations"""
        book = {
            'title': 'Uplifting Tale',
            'genres': ['Self-Help'],
            'description': 'An inspiring journey'
        }
        book_emotions = {'joy': 0.9, 'optimism': 0.8}
        user_emotions = {'sadness': 0.7, 'anxiety': 0.6}
        
        explanation = ExplainabilityEngine.generate_explanation(
            book, book_emotions, user_emotions, 0.75
        )
        
        # Should mention uplifting or mood improvement
        self.assertTrue(
            any(word in explanation.lower() for word in ['uplifting', 'improve', 'mood'])
        )


class TestRecommendationEngine(unittest.TestCase):
    """Test the main recommendation engine"""
    
    @classmethod
    def setUpClass(cls):
        cls.engine = RecommendationEngine(cache_file='test_cache.pkl')
        
        # Create sample books
        cls.sample_books = [
            {
                'book_id': '1',
                'title': 'Happy Adventures',
                'author': 'Joy Writer',
                'genres': ['Adventure', 'Comedy'],
                'description': 'A delightful and joyful adventure full of laughter and fun',
                'average_rating': 4.5
            },
            {
                'book_id': '2',
                'title': 'Peaceful Moments',
                'author': 'Calm Author',
                'genres': ['Fiction', 'Literary'],
                'description': 'A calm and serene story about finding inner peace and tranquility',
                'average_rating': 4.2
            },
            {
                'book_id': '3',
                'title': 'Dark Times',
                'author': 'Serious Writer',
                'genres': ['Drama', 'Tragedy'],
                'description': 'A tragic tale of loss and sorrow in difficult times',
                'average_rating': 4.0
            }
        ]
    
    def test_analyze_book(self):
        """Test single book analysis"""
        book = self.sample_books[0]
        emotions = self.engine.analyze_book(book)
        
        self.assertIsInstance(emotions, dict)
        self.assertGreater(len(emotions), 0)
    
    def test_get_recommendations(self):
        """Test getting recommendations"""
        mood = "I'm feeling happy and want something fun"
        
        recommendations = self.engine.get_recommendations(
            mood,
            self.sample_books,
            top_k=2
        )
        
        # Should return recommendations
        self.assertGreater(len(recommendations), 0)
        self.assertLessEqual(len(recommendations), 2)
        
        # Check recommendation structure
        rec = recommendations[0]
        self.assertIn('book_id', rec)
        self.assertIn('title', rec)
        self.assertIn('sentiment_score', rec)
        self.assertIn('recommendation_reason', rec)
        
        # Scores should be in valid range
        self.assertGreaterEqual(rec['sentiment_score'], 0.0)
        self.assertLessEqual(rec['sentiment_score'], 1.0)
    
    def test_recommendations_sorted(self):
        """Test that recommendations are sorted by score"""
        mood = "I need something calming"
        
        recommendations = self.engine.get_recommendations(
            mood,
            self.sample_books,
            top_k=3
        )
        
        # Should be sorted in descending order
        scores = [rec['sentiment_score'] for rec in recommendations]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_complementary_mode(self):
        """Test complementary recommendations for negative mood"""
        sad_mood = "I'm feeling very sad and depressed"
        
        recommendations = self.engine.get_recommendations(
            sad_mood,
            self.sample_books,
            top_k=2,
            complementary_mode=True
        )
        
        # Should recommend books (might favor uplifting ones)
        self.assertGreater(len(recommendations), 0)


class IntegrationTests(unittest.TestCase):
    """End-to-end integration tests"""
    
    def test_full_workflow_with_sample_data(self):
        """Test complete workflow from mood to recommendations"""
        # Create a small dataset
        books = [
            {
                'book_id': 'test1',
                'title': 'Exciting Adventure',
                'author': 'Adventure Writer',
                'genres': ['Adventure'],
                'description': 'An exciting and thrilling adventure through unknown lands',
                'average_rating': 4.3
            },
            {
                'book_id': 'test2',
                'title': 'Peaceful Garden',
                'author': 'Zen Master',
                'genres': ['Fiction'],
                'description': 'A calming story about a peaceful garden and meditation',
                'average_rating': 4.1
            }
        ]
        
        # Initialize engine
        engine = RecommendationEngine(cache_file='test_integration_cache.pkl')
        
        # Test different moods
        moods = [
            "I want something exciting",
            "I need to relax and feel calm"
        ]
        
        for mood in moods:
            recommendations = engine.get_recommendations(mood, books, top_k=2)
            
            # Should get recommendations
            self.assertGreater(len(recommendations), 0)
            
            # Each should have required fields
            for rec in recommendations:
                self.assertIn('book_id', rec)
                self.assertIn('title', rec)
                self.assertIn('author', rec)
                self.assertIn('sentiment_score', rec)
                self.assertIn('recommendation_reason', rec)
                
                # Explanation should not be empty
                self.assertGreater(len(rec['recommendation_reason']), 10)


def run_tests():
    """Run all tests and print results"""
    print("="*80)
    print("SENTIMENT ANALYSIS MODULE - TEST SUITE")
    print("="*80)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEmotionAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestBookProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestExplainabilityEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestRecommendationEngine))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ All tests passed!")
    else:
        print("\n❌ Some tests failed. See details above.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
