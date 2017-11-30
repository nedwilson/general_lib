import guides
import foundry.ui


viewer_guides = [
  #guides.Guide("title safe", 1, 1, 1, 0.1, guides.kGuideMasked),
  #guides.Guide("action safe", 1, 1, 1, 0.05, guides.kGuideMasked),
  #guides.FormatCenterGuide("format center", 1, 1, 1, 0.1, guides.kGuideSequence,0,offset=.25),
  #guides.Guide("Format", 1, 0, 0, 0, guides.kGuideSequence),
  guides.Guide("CGF",1,1,1,0,guides.kGuideSequence),
]

viewer_masks = [
  #guides.MaskGuide("1.77", 2048.0,1152.0,0.0,0.0),
  #guides.MaskGuide("2.40 raised", 2048.0,852.0,288.0,0.0),
  #guides.MaskGuide("4:3", 4.0/3.0),
  #guides.MaskGuide("16:9", 16.0/9.0),
  #guides.MaskGuide("14:9", 14.0/9.0),
  #guides.MaskGuide("1.66:1", 1.66),
  #guides.MaskGuide("1.85:1", 1.85),
  guides.MaskGuide("2.40:1", 2.4),
  guides.MaskGuide("2.35:1", 2.35),
  guides.MaskGuide("1.77:1", 1.77)
]

