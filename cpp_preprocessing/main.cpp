// cpp_preprocessing/main.cpp
// Owlin Preprocessing Module - Main Pipeline
// C++17, OpenCV 4.x

#include <iostream>
#include <opencv2/opencv.hpp>
#include <vector>
#include <string>

namespace owlin_pre {

// Load image from file path
cv::Mat load_image(const std::string& path) {
    cv::Mat img = cv::imread(path, cv::IMREAD_COLOR);
    if (img.empty()) {
        throw std::runtime_error("Failed to load image: " + path);
    }
    return img;
}

// Convert to grayscale
cv::Mat to_grayscale(const cv::Mat& img) {
    cv::Mat gray;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    return gray;
}

// Resize image to 150% using bicubic interpolation
cv::Mat resize_image(const cv::Mat& img) {
    cv::Mat resized;
    cv::resize(img, resized, cv::Size(), 1.5, 1.5, cv::INTER_CUBIC);
    return resized;
}

// Apply adaptive Gaussian thresholding
cv::Mat adaptive_threshold(const cv::Mat& img) {
    cv::Mat thresh;
    cv::adaptiveThreshold(
        img, thresh,
        255,
        cv::ADAPTIVE_THRESH_GAUSSIAN_C,
        cv::THRESH_BINARY,
        31, // block size
        10  // C value
    );
    return thresh;
}

// Deskew image using minAreaRect on non-zero pixels
cv::Mat deskew(const cv::Mat& bin_img) {
    std::vector<cv::Point> points;
    cv::findNonZero(bin_img, points);
    if (points.empty()) {
        // Nothing to deskew
        return bin_img.clone();
    }
    cv::RotatedRect box = cv::minAreaRect(points);
    float angle = box.angle;
    if (angle < -45.0f) angle += 90.0f;
    cv::Mat rot_mat = cv::getRotationMatrix2D(box.center, angle, 1.0);
    cv::Mat rotated;
    cv::warpAffine(bin_img, rotated, rot_mat, bin_img.size(), cv::INTER_CUBIC, cv::BORDER_REPLICATE);
    return rotated;
}

// Print image info (dimensions and channels)
void print_image_info(const cv::Mat& img, const std::string& label) {
    std::cout << label << ": " << img.cols << " x " << img.rows << " (channels: " << img.channels() << ")\n";
}

// Main preprocessing pipeline
cv::Mat preprocessImage(const std::string& filepath) {
    // Load image
    cv::Mat img = load_image(filepath);
    print_image_info(img, "Loaded image");

    // Grayscale
    cv::Mat gray = to_grayscale(img);
    print_image_info(gray, "Grayscale image");

    // Resize
    cv::Mat resized = resize_image(gray);
    print_image_info(resized, "Resized grayscale image (150%)");

    // Adaptive threshold
    cv::Mat thresh = adaptive_threshold(resized);
    print_image_info(thresh, "Adaptive Gaussian Thresholded image");

    // Deskew
    cv::Mat deskewed = deskew(thresh);
    print_image_info(deskewed, "Deskewed image");

    return deskewed;
}

} // namespace owlin_pre

#ifdef __cplusplus
extern "C" {
#endif

unsigned char* preprocess_image(const char* filepath, int* width, int* height, int* channels) {
    try {
        cv::Mat img = owlin_pre::preprocessImage(filepath);
        if (img.empty()) {
            return nullptr;
        }

        // Allocate memory for the grayscale image data
        int img_size = img.total() * img.channels();
        unsigned char* buffer = (unsigned char*)malloc(img_size);
        if (!buffer) {
            return nullptr;
        }

        // Copy image data into the buffer
        if (img.isContinuous()) {
            memcpy(buffer, img.data, img_size);
        } else {
            // If image is not continuous, copy row by row
            for (int i = 0; i < img.rows; ++i) {
                memcpy(buffer + i * img.cols * img.channels(), img.ptr(i), img.cols * img.channels());
            }
        }

        // Set width, height, and channels
        *width = img.cols;
        *height = img.rows;
        *channels = img.channels();

        return buffer;
    } catch (const std::exception& ex) {
        std::cerr << "Error in preprocess_image: " << ex.what() << std::endl;
        return nullptr;
    }
}

#ifdef __cplusplus
}
#endif 

---

**How this integrates with Owlin Streamlit:**
- Use this script (or its logic) to preprocess invoice images before OCR.
- The returned numpy array or bytes can be passed to `st.image` or further processed in Python.
- No external Tesseract dependency is needed for preprocessing.

**Key points:**
- Handles cross-platform library loading and memory management.
- Provides robust error handling and clear comments.
- Ready for direct use or adaptation in your Streamlit app.

Let me know if you want a version that wraps this as a Streamlit component or further integration help!

import ctypes
import sys
import os
import platform

# --- Detect OS and load the shared library ---
if sys.platform.startswith("win"):
    libname = "preprocess.dll"
elif sys.platform == "darwin":
    libname = "libpreprocess.dylib"
else:
    libname = "libpreprocess.so"

# Adjust the path as needed (assumes library is in the same directory)
libpath = os.path.join(os.path.dirname(__file__), libname)
lib = ctypes.CDLL(libpath)

# --- Define the preprocess_image function prototype ---
# int preprocess_image(const char* filepath, int* width, int* height, int* channels)
lib.preprocess_image.restype = ctypes.POINTER(ctypes.c_ubyte)
lib.preprocess_image.argtypes = [
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int)
]

# --- Helper function to free memory allocated by C/C++ ---
def free_c_buffer(ptr):
    if not ptr:
        return
    if sys.platform.startswith("win"):
        # On Windows, use msvcrt's free
        ctypes.windll.msvcrt.free(ptr)
    else:
        # On Linux/macOS, use libc's free
        ctypes.CDLL(None).free(ptr)

# --- Example usage ---
def main():
    # Path to the invoice image (update as needed)
    image_path = "test_invoice.jpg"
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return

    # Prepare output variables
    width = ctypes.c_int()
    height = ctypes.c_int()
    channels = ctypes.c_int()

    # Call the C API function
    ptr = lib.preprocess_image(
        image_path.encode("utf-8"),
        ctypes.byref(width),
        ctypes.byref(height),
        ctypes.byref(channels)
    )

    if not ptr:
        print("Preprocessing failed or returned no data.")
        return

    # Copy the data into a Python bytes object or numpy array
    nbytes = width.value * height.value * channels.value
    try:
        import numpy as np
        arr = np.ctypeslib.as_array(ptr, shape=(height.value, width.value, channels.value))
        # Optionally, copy to a new array if you want to own the data
        arr = arr.copy()
        print(f"Preprocessed image shape: {arr.shape}, dtype: {arr.dtype}")
    except ImportError:
        # Fallback: just get as bytes
        arr = ctypes.string_at(ptr, nbytes)
        print(f"Preprocessed image: {width.value}x{height.value}x{channels.value}, {len(arr)} bytes")

    # Free the buffer allocated by C++
    free_c_buffer(ptr)

    # You can now use 'arr' in your Streamlit app, e.g. with st.image(arr, ...)

if __name__ == "__main__":
    main() 