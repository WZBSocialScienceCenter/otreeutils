# Example implementation for an experiment with dynamically determined data quantity in oTree

July/Sept. 2018, Markus Konrad <markus.konrad@wzb.eu> / [Berlin Social Science Center](https://wzb.eu)

This repository contains the companion code for the article [*oTree: Implementing experiments with dynamically determined data quantity*](https://doi.org/10.1016/j.jbef.2018.10.006) published in a Special Issue on "Software for Experimental Economics" in the *Journal of Behavioral and Experimental Finance*.

The experiment "market" that is provided as [oTree](http://www.otree.org/) application serves as a illustrative example for a simple stylized market simulation. Many individuals (1 ... *N*-1) are selling fruit. In each round, these sellers choose a kind of fruit and a selling price, whereas individual *N* (the buyer) needs to choose from which of those offers to buy. The implemenation follows the principle suggested in the paper, relying on "custom data models" from oTree's underlying Django framework.

This project also illustrates how the admin interface extensions of the package *[otreeutils](https://github.com/WZBSocialScienceCenter/otreeutils)* can be integrated in an experiment. This adds the functionality to observe data updates from custom data models in oTree's "session data viewer". Additionally, data exports for CSV and Excel contain all data from custom data models and an option to export the data in JSON format is available.   

**Please note:** This is not a complete experiment but only a stripped-down example for illustrative purposes. This means for example that some sanity checks like checking for negative balances are not implemented.

## Requirements

This project requires otree and [otreeutils 0.5 or newer](https://github.com/WZBSocialScienceCenter/otreeutils).

The code has been tested with oTree v2.1.14 but should run with any oTree version of at least v2.0. 

## License

Apache License 2.0. See LICENSE file.
