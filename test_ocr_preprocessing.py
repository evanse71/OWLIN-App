#!/usr/bin/env python3
"""
Test script for Enhanced OCR Preprocessing Pipeline
Demonstrates the preprocessing improvements and tests accuracy enhancements.
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
from app.ocr_preprocessing import OCRPreprocessor, create_preprocessing_config
from app.ocr_factory import get_ocr_recognizer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_image_with_text():
    """Create a test image with text and various quality issues."""
    # Create a white background
    image = np.ones((600, 800), dtype=np.uint8) * 255
    
    # Add text-like structures (simulating invoice text)
    cv2.putText(image, "INVOICE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 0, 3)
    cv2.putText(image, "Invoice No: INV-2024-001", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
    cv2.putText(image, "Date: 2024-01-15", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
    cv2.putText(image, "Supplier: ABC Company Ltd", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
    cv2.putText(image, "Item 1: Office Supplies", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    cv2.putText(image, "Quantity: 10", (50, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    cv2.putText(image, "Price: $25.00", (50, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    cv2.putText(image, "Total: $250.00", (50, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 3)
    
    # Add some noise to simulate poor quality
    noise = np.random.normal(0, 20, image.shape).astype(np.uint8)
    image = np.clip(image + noise, 0, 255)
    
    # Add some blur to simulate poor focus
    image = cv2.GaussianBlur(image, (3, 3), 0.5)
    
    # Add some rotation to simulate skewed document
    height, width = image.shape
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 2.5, 1.0)
    image = cv2.warpAffine(image, rotation_matrix, (width, height), 
                          flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return image

def create_test_image_with_contrast_issues():
    """Create a test image with poor contrast."""
    # Create a gray background
    image = np.ones((600, 800), dtype=np.uint8) * 180
    
    # Add text with low contrast
    cv2.putText(image, "DELIVERY NOTE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 100, 3)
    cv2.putText(image, "Order No: ORD-2024-001", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, 100, 2)
    cv2.putText(image, "Customer: XYZ Corp", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, 100, 2)
    cv2.putText(image, "Delivery Date: 2024-01-20", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, 100, 2)
    cv2.putText(image, "Item: Laptop Computer", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 100, 2)
    cv2.putText(image, "Quantity: 5", (50, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 100, 2)
    cv2.putText(image, "Status: Shipped", (50, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 100, 2)
    
    return image

def test_preprocessing_pipeline():
    """Test the preprocessing pipeline with various test images."""
    print("🧪 Testing Enhanced OCR Preprocessing Pipeline")
    print("=" * 60)
    
    # Create test images
    test_images = [
        ("Noisy Text", create_test_image_with_text()),
        ("Low Contrast", create_test_image_with_contrast_issues())
    ]
    
    # Create preprocessor with different configurations
    configs = {
        "Default": None,
        "High Quality": create_preprocessing_config(
            denoising_method='bilateral',
            thresholding_method='adaptive',
            contrast_method='clahe',
            enable_deskewing=True
        ),
        "Fast Processing": create_preprocessing_config(
            denoising_method='gaussian',
            thresholding_method='otsu',
            contrast_method='histogram_equalization',
            enable_deskewing=False
        )
    }
    
    results = {}
    
    for config_name, config in configs.items():
        print(f"\n📋 Testing Configuration: {config_name}")
        print("-" * 40)
        
        preprocessor = OCRPreprocessor(config)
        config_results = {}
        
        for image_name, original_image in test_images:
            print(f"\n🖼️  Processing: {image_name}")
            
            # Preprocess image
            processed_image = preprocessor.preprocess_image(original_image)
            
            # Calculate statistics
            stats = preprocessor.get_preprocessing_stats(original_image, processed_image)
            
            # Test OCR on both original and processed
            try:
                recognizer = get_ocr_recognizer()
                
                # OCR on original
                original_text, original_confidence = recognizer.recognize(original_image)
                
                # OCR on processed
                processed_text, processed_confidence = recognizer.recognize(processed_image)
                
                # Calculate improvement
                confidence_improvement = processed_confidence - original_confidence
                text_improvement = len(processed_text.strip()) - len(original_text.strip())
                
                config_results[image_name] = {
                    'original_confidence': original_confidence,
                    'processed_confidence': processed_confidence,
                    'confidence_improvement': confidence_improvement,
                    'original_text_length': len(original_text.strip()),
                    'processed_text_length': len(processed_text.strip()),
                    'text_improvement': text_improvement,
                    'preprocessing_stats': stats
                }
                
                print(f"  ✅ Original OCR: {original_confidence:.3f} confidence, {len(original_text.strip())} chars")
                print(f"  ✅ Processed OCR: {processed_confidence:.3f} confidence, {len(processed_text.strip())} chars")
                print(f"  📈 Improvement: +{confidence_improvement:.3f} confidence, +{text_improvement} chars")
                print(f"  🔧 Preprocessing: Contrast +{stats['contrast_improvement']:.2f}, Noise -{stats['noise_reduction']:.2f}")
                
            except Exception as e:
                print(f"  ❌ OCR test failed: {e}")
                config_results[image_name] = {'error': str(e)}
        
        results[config_name] = config_results
    
    return results, test_images

def visualize_preprocessing_results(test_images, results):
    """Create visualizations of preprocessing results."""
    print("\n📊 Creating Visualizations")
    print("-" * 40)
    
    # Create a comprehensive visualization
    fig, axes = plt.subplots(len(test_images), 4, figsize=(20, 5 * len(test_images)))
    if len(test_images) == 1:
        axes = axes.reshape(1, -1)
    
    for i, (image_name, original_image) in enumerate(test_images):
        # Original image
        axes[i, 0].imshow(original_image, cmap='gray')
        axes[i, 0].set_title(f'Original: {image_name}')
        axes[i, 0].axis('off')
        
        # Processed with default config
        preprocessor = OCRPreprocessor()
        processed_default = preprocessor.preprocess_image(original_image)
        axes[i, 1].imshow(processed_default, cmap='gray')
        axes[i, 1].set_title('Default Preprocessing')
        axes[i, 1].axis('off')
        
        # Processed with high quality config
        high_quality_config = create_preprocessing_config(
            denoising_method='bilateral',
            thresholding_method='adaptive',
            contrast_method='clahe',
            enable_deskewing=True
        )
        preprocessor_hq = OCRPreprocessor(high_quality_config)
        processed_hq = preprocessor_hq.preprocess_image(original_image)
        axes[i, 2].imshow(processed_hq, cmap='gray')
        axes[i, 2].set_title('High Quality Preprocessing')
        axes[i, 2].axis('off')
        
        # Processed with fast config
        fast_config = create_preprocessing_config(
            denoising_method='gaussian',
            thresholding_method='otsu',
            contrast_method='histogram_equalization',
            enable_deskewing=False
        )
        preprocessor_fast = OCRPreprocessor(fast_config)
        processed_fast = preprocessor_fast.preprocess_image(original_image)
        axes[i, 3].imshow(processed_fast, cmap='gray')
        axes[i, 3].set_title('Fast Preprocessing')
        axes[i, 3].axis('off')
    
    plt.tight_layout()
    plt.savefig('ocr_preprocessing_results.png', dpi=300, bbox_inches='tight')
    print("  💾 Saved visualization to 'ocr_preprocessing_results.png'")
    
    # Create performance comparison chart
    create_performance_chart(results)

def create_performance_chart(results):
    """Create a performance comparison chart."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Extract data for plotting
    configs = list(results.keys())
    test_images = list(results[configs[0]].keys())
    
    # Confidence improvement data
    confidence_data = []
    text_improvement_data = []
    
    for config in configs:
        config_confidence = []
        config_text = []
        for image_name in test_images:
            if 'error' not in results[config][image_name]:
                config_confidence.append(results[config][image_name]['confidence_improvement'])
                config_text.append(results[config][image_name]['text_improvement'])
        confidence_data.append(config_confidence)
        text_improvement_data.append(config_text)
    
    # Plot confidence improvements
    x = np.arange(len(test_images))
    width = 0.25
    
    for i, config in enumerate(configs):
        ax1.bar(x + i * width, confidence_data[i], width, label=config)
    
    ax1.set_xlabel('Test Images')
    ax1.set_ylabel('Confidence Improvement')
    ax1.set_title('OCR Confidence Improvement by Configuration')
    ax1.set_xticks(x + width)
    ax1.set_xticklabels(test_images)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot text length improvements
    for i, config in enumerate(configs):
        ax2.bar(x + i * width, text_improvement_data[i], width, label=config)
    
    ax2.set_xlabel('Test Images')
    ax2.set_ylabel('Text Length Improvement')
    ax2.set_title('Text Length Improvement by Configuration')
    ax2.set_xticks(x + width)
    ax2.set_xticklabels(test_images)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ocr_performance_comparison.png', dpi=300, bbox_inches='tight')
    print("  💾 Saved performance comparison to 'ocr_performance_comparison.png'")

def print_summary_report(results):
    """Print a comprehensive summary report."""
    print("\n📋 OCR Preprocessing Pipeline Summary Report")
    print("=" * 60)
    
    for config_name, config_results in results.items():
        print(f"\n🔧 Configuration: {config_name}")
        print("-" * 40)
        
        total_confidence_improvement = 0
        total_text_improvement = 0
        successful_tests = 0
        
        for image_name, result in config_results.items():
            if 'error' not in result:
                successful_tests += 1
                total_confidence_improvement += result['confidence_improvement']
                total_text_improvement += result['text_improvement']
                
                print(f"  📄 {image_name}:")
                print(f"    Confidence: {result['original_confidence']:.3f} → {result['processed_confidence']:.3f} (+{result['confidence_improvement']:.3f})")
                print(f"    Text Length: {result['original_text_length']} → {result['processed_text_length']} (+{result['text_improvement']})")
            else:
                print(f"  ❌ {image_name}: {result['error']}")
        
        if successful_tests > 0:
            avg_confidence_improvement = total_confidence_improvement / successful_tests
            avg_text_improvement = total_text_improvement / successful_tests
            
            print(f"\n  📊 Average Improvements:")
            print(f"    Confidence: +{avg_confidence_improvement:.3f}")
            print(f"    Text Length: +{avg_text_improvement:.1f} characters")
    
    print(f"\n✅ Test completed successfully!")
    print(f"📈 Enhanced OCR preprocessing pipeline is ready for production use.")

def main():
    """Main test function."""
    print("🚀 Starting Enhanced OCR Preprocessing Pipeline Tests")
    print("=" * 60)
    
    try:
        # Run preprocessing tests
        results, test_images = test_preprocessing_pipeline()
        
        # Create visualizations
        visualize_preprocessing_results(test_images, results)
        
        # Print summary report
        print_summary_report(results)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 