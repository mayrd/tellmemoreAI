import podcast2video
import media

if __name__ == "__main__":
    podcast2video.gen_thumbnail(
        "The podcast episode discovers the invention of soap",
        "Soap",
        "#KnowledgeDrop",
        "test.jpg"
    )
    #media.image_add_text_centered(
    #    "test.jpg", "Title", "fonts/FingerPaint-Regular.ttf", 200,
    #    border_width = 2,
    #    offset_x= 40, offset_y = 40
    #)
    #media.image_add_text(
    #    "test.jpg", "#KnowledgeDrop", "fonts/FingerPaint-Regular.ttf", 180,
    #    border_width = 2,
    #    pos_x= 0, pos_y = 0
    #)