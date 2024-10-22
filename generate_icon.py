from PIL import Image, ImageDraw, ImageFont
import os

def create_car_icon(output_file="car_icon.png", size=(32, 32), bg_color="white", text_color="black"):
    # Create a new image with a white background
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)

    # Load the ASCII art
    with open("car_icon.txt", "r") as f:
        ascii_art = f.read()

    # Calculate font size
    font_size = 1
    font = ImageFont.load_default()
    while font.getbbox(ascii_art.split('\n')[0])[2] < size[0] and font.getbbox(ascii_art)[3] < size[1]:
        font_size += 1
        font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)

    # Draw the ASCII art
    draw.text((0, 0), ascii_art, font=font, fill=text_color)

    # Save the image
    img.save(output_file)
    print(f"Car icon saved as {output_file}")

if __name__ == "__main__":
    create_car_icon()
