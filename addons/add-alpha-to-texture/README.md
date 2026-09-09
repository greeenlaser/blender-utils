# Add alpha to texture

This is a full blender addon and can be added to Blender 4.5.x (and probably newer and older versions, but untested).

This utility adds a new node called `Add Alpha To Texture` with two modes: Material, Image.

Material is meant as a "preview" of what the final texture looks like, it takes in a base texture in the Image input and a value or image to the Alpha input field and outputs Color and Alpha.

Image does not have outputs, takes the same inputs as Material but has a button for generating a new blender internal texture with your chosen name, size and alpha channel target. Use this mode to actually generate a texture you intend to use for your target model.
