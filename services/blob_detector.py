import cv2
import math
import argparse

class CircleDetector:
    def __init__(self, minArea, minCircularity, minInertiaRatio, minConvexity):
        # Initialize SimpleBlobDetector with given parameters
        params = cv2.SimpleBlobDetector_Params()
        # Filter by area (size)
        params.filterByArea = True
        params.minArea = minArea
        params.maxArea = 1e9  # large upper bound to not exclude big circles
        # Filter by circularity (roundness)
        params.filterByCircularity = True
        params.minCircularity = minCircularity
        # Filter by convexity (shape must be largely convex)
        params.filterByConvexity = True
        params.minConvexity = minConvexity
        # Filter by inertia (not too elongated)
        params.filterByInertia = True
        params.minInertiaRatio = minInertiaRatio
        # Filter by color (look for bright (white) blobs on dark background)
        params.filterByColor = True
        params.blobColor = 255
        # Set threshold range for internal blob detection
        params.minThreshold = 10
        params.maxThreshold = 255
        params.thresholdStep = 10
        # Create the detector with the parameters
        self.detector = cv2.SimpleBlobDetector_create(params)
    
    def detect_and_draw(self, image_path, output_path=None, show=False):
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Input image '{image_path}' not found.")
        # Convert to grayscale for detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
# Apply slight Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive Gaussian Thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            21,  # blockSize (larger block size if larger circles)
            2    # constant C, fine-tune this slightly if needed
        )

        # Invert thresholding if circles appear dark instead of bright
        # thresh = cv2.bitwise_not(thresh)

        # Morphological opening to remove noise (optional but often beneficial)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

        
        # Detect blobs on the thresholded image
        keypoints = self.detector.detect(thresh)
        
        # Filter out keypoints that touch image borders (incomplete circles)
        h, w = gray.shape
        valid_keypoints = []
        for kp in keypoints:
            x, y, r = kp.pt[0], kp.pt[1], kp.size / 2.0
            if (x - r) < 0 or (y - r) < 0 or (x + r) > w - 1 or (y + r) > h - 1:
                continue  # skip incomplete blobs
            valid_keypoints.append(kp)
        keypoints = valid_keypoints

        # Draw rectangles around detected circles
        draw_img = image.copy()
        for kp in keypoints:
            x, y = int(kp.pt[0]), int(kp.pt[1])
            r = int(math.ceil(kp.size / 2.0))
            cv2.rectangle(draw_img, (x - r, y - r), (x + r, y + r), (0, 255, 0), 2)

        # Overlay circle count
        count = len(keypoints)
        cv2.putText(draw_img, f"Circles: {count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        # Save output image
        if output_path:
            out_path = output_path
        else:
            dot_index = image_path.rfind('.')
            out_path = image_path[:dot_index] + "_detected" + image_path[dot_index:]
        cv2.imwrite(out_path, draw_img)

        # Display image if needed
        if show:
            cv2.imshow("Detected Circles", draw_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        return count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect circles in an image using cv2.SimpleBlobDetector")
    parser.add_argument("--input", "-i", required=True, help="Path to the input image")
    parser.add_argument("--output", "-o", help="Path to save the output image with detected circles")
    parser.add_argument("--minArea", type=float, required=True, help="Minimum area of circles to detect (in pixels)")
    parser.add_argument("--minCircularity", type=float, required=True, help="Minimum circularity [0,1] to filter blobs")
    parser.add_argument("--minConvexity", type=float, required=True, help="Minimum convexity [0,1] to filter blobs")
    parser.add_argument("--minInertiaRatio", type=float, required=True, help="Minimum inertia ratio [0,1] to filter blobs")
    args = parser.parse_args()
    # Create detector with specified parameters
    detector = CircleDetector(args.minArea, args.minCircularity, args.minInertiaRatio, args.minConvexity)
    # Run detection and drawing
    count = detector.detect_and_draw(args.input, args.output, show=True)
    print(f"Detected {count} circles.")
